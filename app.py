import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import json

# 데이터베이스 초기화 및 마이그레이션
def init_database():
    conn = sqlite3.connect('coffee_tracker.db')
    cursor = conn.cursor()
    
    # 원두 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            shop TEXT,
            variety TEXT,
            roast_date DATE,
            notes TEXT,
            created_date DATE
        )
    ''')
    
    # 추출 기록 테이블 (기본 구조)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brewing_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bean_id INTEGER,
            brew_date DATE,
            grind_size TEXT,
            coffee_amount REAL,
            water_amount REAL,
            water_temp REAL,
            brew_time TEXT,
            method TEXT,
            taste_score INTEGER,
            aroma_score INTEGER,
            body_score INTEGER,
            acidity_score INTEGER,
            overall_score INTEGER,
            tasting_notes TEXT,
            improvements TEXT,
            FOREIGN KEY (bean_id) REFERENCES beans (id)
        )
    ''')
    
    # 기존 테이블에 새로운 컬럼들 추가 (마이그레이션)
    try:
        # equipment 컬럼 추가
        cursor.execute("ALTER TABLE brewing_records ADD COLUMN equipment TEXT")
    except sqlite3.OperationalError:
        pass  # 이미 존재하면 무시
    
    try:
        # adding_water 컬럼 추가
        cursor.execute("ALTER TABLE brewing_records ADD COLUMN adding_water REAL")
    except sqlite3.OperationalError:
        pass  # 이미 존재하면 무시
    
    try:
        # pour_schedule 컬럼 추가
        cursor.execute("ALTER TABLE brewing_records ADD COLUMN pour_schedule TEXT")
    except sqlite3.OperationalError:
        pass  # 이미 존재하면 무시
    
    # grind_size 타입을 TEXT에서 INTEGER로 변경하는 것은 복잡하므로,
    # 기존 데이터와 호환성을 위해 TEXT로 유지하고 저장할 때 문자열로 변환
    
    conn.commit()
    conn.close()

# 원두 저장 함수 (누락된 함수 추가)
def save_bean(name, shop, variety, roast_date, notes):
    conn = sqlite3.connect('coffee_tracker.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO beans (name, shop, variety, roast_date, notes, created_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, shop, variety, roast_date, notes, date.today()))
    
    conn.commit()
    conn.close()
    st.success("원두가 등록되었습니다!")

# 원두 삭제
def delete_bean(bean_id):
    conn = sqlite3.connect('coffee_tracker.db')
    cursor = conn.cursor()
    
    # 해당 원두의 추출 기록도 함께 삭제
    cursor.execute("DELETE FROM brewing_records WHERE bean_id = ?", (bean_id,))
    cursor.execute("DELETE FROM beans WHERE id = ?", (bean_id,))
    
    conn.commit()
    conn.close()
    st.success("원두와 관련 추출 기록이 모두 삭제되었습니다!")

# 추출 기록 삭제 (수정됨)
def delete_brewing_record(record_id):
    conn = sqlite3.connect('coffee_tracker.db')
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM brewing_records WHERE id = ?", (record_id,))
    
    conn.commit()
    conn.close()
    st.success("추출 기록이 삭제되었습니다!")

# 추출 기록 저장
def save_brewing_record(bean_id, brew_date, grind_size, coffee_amount, 
                       water_temp, brew_time, method, equipment, adding_water, pour_schedule,
                       taste_score, aroma_score, body_score, acidity_score, overall_score, 
                       tasting_notes, improvements):
    conn = sqlite3.connect('coffee_tracker.db')
    cursor = conn.cursor()
    
    # pour_schedule을 JSON 문자열로 변환
    pour_schedule_json = json.dumps(pour_schedule) if pour_schedule else None
    
    cursor.execute('''
        INSERT INTO brewing_records (bean_id, brew_date, grind_size, coffee_amount, 
                                   water_temp, brew_time, method, equipment,
                                   adding_water, pour_schedule, taste_score, aroma_score, 
                                   body_score, acidity_score, overall_score, tasting_notes, improvements)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (bean_id, brew_date, str(grind_size), coffee_amount, water_temp, 
          brew_time, method, equipment, adding_water, pour_schedule_json, taste_score, 
          aroma_score, body_score, acidity_score, overall_score, tasting_notes, improvements))
    
    conn.commit()
    conn.close()
    st.success("추출 기록이 저장되었습니다!")

# 원두 목록 가져오기 (최신순 정렬 강화)
def get_beans():
    conn = sqlite3.connect('coffee_tracker.db')
    # created_date가 NULL인 경우를 대비해 id로도 정렬
    df = pd.read_sql_query("""
        SELECT * FROM beans 
        ORDER BY 
            CASE WHEN created_date IS NULL THEN 1 ELSE 0 END,
            created_date DESC, 
            id DESC
    """, conn)
    conn.close()
    return df

# 특정 원두의 추출 기록 가져오기 (최신순 정렬 강화)
def get_brewing_records(bean_id=None):
    conn = sqlite3.connect('coffee_tracker.db')
    if bean_id:
        query = '''
            SELECT br.*, b.name as bean_name 
            FROM brewing_records br 
            JOIN beans b ON br.bean_id = b.id 
            WHERE br.bean_id = ?
            ORDER BY 
                CASE WHEN br.brew_date IS NULL THEN 1 ELSE 0 END,
                br.brew_date DESC, 
                br.id DESC
        '''
        df = pd.read_sql_query(query, conn, params=(bean_id,))
    else:
        query = '''
            SELECT br.*, b.name as bean_name 
            FROM brewing_records br 
            JOIN beans b ON br.bean_id = b.id 
            ORDER BY 
                CASE WHEN br.brew_date IS NULL THEN 1 ELSE 0 END,
                br.brew_date DESC, 
                br.id DESC
        '''
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 특정 원두 정보 가져오기
def get_bean_info(bean_id):
    conn = sqlite3.connect('coffee_tracker.db')
    query = "SELECT * FROM beans WHERE id = ?"
    df = pd.read_sql_query(query, conn, params=(bean_id,))
    conn.close()
    return df.iloc[0] if not df.empty else None

# 커핑 노트 템플릿 데이터
def get_cupping_notes_template():
    return {
        "향 (Aroma)": [
            "과일향", "베리류", "시트러스", "사과", "체리", "포도", 
            "꽃향", "자스민", "라벤더", "장미",
            "견과류", "아몬드", "헤이즐넛", "피칸",
            "초콜릿", "다크초콜릿", "밀크초콜릿", "코코아",
            "캐러멜", "바닐라", "꿀", "메이플시럽"
        ],
        "맛 (Taste)": [
            "단맛", "신맛", "쓴맛", "짠맛", "감칠맛",
            "과일단맛", "설탕단맛", "꿀단맛",
            "밝은신맛", "부드러운신맛", "날카로운신맛",
            "깔끔한쓴맛", "진한쓴맛", "뒷맛쓴맛"
        ],
        "바디감 (Body)": [
            "가벼움", "중간", "진함", "크리미", "실키", 
            "오일리", "물같음", "시럽같음", "벨벳같음"
        ],
        "산미 (Acidity)": [
            "밝은산미", "부드러운산미", "날카로운산미", "과일산미",
            "시트릭산미", "사과산미", "와인산미", "균형잡힌산미"
        ],
        "후미 (Aftertaste)": [
            "깔끔함", "여운있음", "지속적", "단맛여운", 
            "쓴맛여운", "과일여운", "초콜릿여운", "견과류여운"
        ],
        "특별한맛": [
            "스파이시", "허브", "로즈마리", "민트", "계피",
            "담배", "가죽", "흙냄새", "나무", "연기맛",
            "토스트", "구운맛", "카라멜화", "로스팅"
        ]
    }

# 커핑 태그 선택 위젯
def cupping_tags_selector():
    template = get_cupping_notes_template()
    
    st.subheader("☕ 커핑 노트 템플릿")
    st.markdown("*태그를 클릭해서 선택하세요! 선택된 태그들이 테이스팅 노트에 자동으로 추가됩니다.*")
    
    for category, tags in template.items():
        with st.expander(f"📝 {category}", expanded=False):
            cols = st.columns(3)  # 모바일에서 3열로 배치
            
            for i, tag in enumerate(tags):
                with cols[i % 3]:
                    is_selected = tag in st.session_state.selected_cupping_tags
                    
                    if st.button(
                        tag, 
                        key=f"tag_{category}_{tag}",
                        help=f"{category}에서 {tag} 선택/해제",
                        use_container_width=True
                    ):
                        if is_selected:
                            st.session_state.selected_cupping_tags.remove(tag)
                        else:
                            st.session_state.selected_cupping_tags.append(tag)
                        st.rerun()
                    
                    # 선택된 태그 시각적 표시
                    if is_selected:
                        st.markdown(f"<div style='text-align:center; color:green; font-size:0.8rem;'>✅</div>", 
                                  unsafe_allow_html=True)
    
    # 선택된 태그들 미리보기
    if st.session_state.selected_cupping_tags:
        st.success(f"**선택된 태그들:** {', '.join(st.session_state.selected_cupping_tags)}")
        
        # 태그 초기화 버튼
        if st.button("🗑️ 선택된 태그 모두 지우기"):
            st.session_state.selected_cupping_tags = []
            st.rerun()
    
    return ', '.join(st.session_state.selected_cupping_tags)

# 메인 앱
def main():
    st.set_page_config(
        page_title="☕ 커피 추출 기록", 
        layout="wide",
        initial_sidebar_state="collapsed"  # 모바일에서 사이드바 기본 접힘
    )
    
    # 모바일 최적화 CSS (단순한 스타일)
    st.markdown("""
    <style>
    /* 모바일 최적화 스타일 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* 버튼 크기 증가 */
    .stButton > button {
        height: 3rem;
        font-size: 1.1rem;
        border-radius: 10px;
    }
    
    /* 카드 스타일 개선 */
    .coffee-card {
        padding: 1.5rem;
        border: 2px solid #ddd;
        border-radius: 15px;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 모바일에서 폰트 크기 조정 */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        .stButton > button {
            height: 3.5rem;
            font-size: 1.2rem;
        }
        
        .coffee-card h4 {
            font-size: 1.3rem;
        }
        
        .coffee-card p {
            font-size: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 데이터베이스 초기화
    init_database()
    
    # 세션 상태 초기화
    if 'selected_bean_id' not in st.session_state:
        st.session_state.selected_bean_id = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 홈"
    if 'pour_schedule' not in st.session_state:
        st.session_state.pour_schedule = [{'water_amount': 40, 'time': '0:00'}]
    if 'selected_cupping_tags' not in st.session_state:
        st.session_state.selected_cupping_tags = []
    
    st.title("☕ 커피 추출 기록")
    
    # 현재 페이지에 따른 메뉴 옵션 구성
    if st.session_state.selected_bean_id:
        bean_info = get_bean_info(st.session_state.selected_bean_id)
        if bean_info is not None:
            tab_options = ["🏠 홈", f"☕ {bean_info['name'][:8]}... 추출", "🫘 원두 등록", "📊 기록 보기", "📈 통계"]
        else:
            tab_options = ["🏠 홈", "🫘 원두 등록", "📊 기록 보기", "📈 통계"]
    else:
        tab_options = ["🏠 홈", "🫘 원두 등록", "📊 기록 보기", "📈 통계"]
    
    # 현재 페이지에 맞는 인덱스 찾기
    current_index = 0
    if "추출하기" in st.session_state.current_page:
        current_index = 1 if len(tab_options) > 1 and "추출" in tab_options[1] else 0
    elif st.session_state.current_page == "🫘 원두 등록":
        current_index = tab_options.index("🫘 원두 등록") if "🫘 원두 등록" in tab_options else 0
    elif st.session_state.current_page == "📊 추출 기록 보기":
        current_index = tab_options.index("📊 기록 보기") if "📊 기록 보기" in tab_options else 0
    elif st.session_state.current_page == "📈 통계":
        current_index = tab_options.index("📈 통계") if "📈 통계" in tab_options else 0
    
    # 탭으로 메뉴 변경 (모바일에서 더 편함)
    selected_tab = st.selectbox(
        "📱 메뉴 선택",
        tab_options,
        index=current_index,
        label_visibility="collapsed"
    )
    
    # 페이지 라우팅
    if selected_tab == "🏠 홈":
        menu = "🏠 홈"
        st.session_state.current_page = "🏠 홈"
    elif selected_tab == "🫘 원두 등록":
        menu = "🫘 원두 등록"
        st.session_state.current_page = "🫘 원두 등록"
    elif selected_tab == "📊 기록 보기":
        menu = "📊 추출 기록 보기"
        st.session_state.current_page = "📊 추출 기록 보기"
    elif selected_tab == "📈 통계":
        menu = "📈 통계"
        st.session_state.current_page = "📈 통계"
    elif "추출" in selected_tab and st.session_state.selected_bean_id:
        bean_info = get_bean_info(st.session_state.selected_bean_id)
        if bean_info is not None:
            menu = f"☕ {bean_info['name']} 추출하기"
            st.session_state.current_page = menu
    else:
        menu = "🏠 홈"
        st.session_state.current_page = "🏠 홈"
    
    st.markdown("---")
    
    if menu == "🏠 홈":
        st.header("등록된 원두 목록 ☕")
        
        beans_df = get_beans()
        brewing_records_df = get_brewing_records()
        
        # 요약 정보
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("등록된 원두", len(beans_df))
        with col2:
            st.metric("총 추출 횟수", len(brewing_records_df))
        with col3:
            if not brewing_records_df.empty:
                avg_score = brewing_records_df['overall_score'].mean()
                st.metric("평균 만족도", f"{avg_score:.1f}/5")
            else:
                st.metric("평균 만족도", "0/5")
        
        st.markdown("---")
        
        if not beans_df.empty:
            st.subheader("☕ 원두를 터치해서 추출을 시작하세요!")
            
            # 모바일 최적화: 1열 또는 2열로 배치
            for idx, (_, bean) in enumerate(beans_df.iterrows()):
                # 해당 원두의 추출 횟수 계산
                bean_records = brewing_records_df[brewing_records_df['bean_id'] == bean['id']]
                brew_count = len(bean_records)
                last_brew = bean_records['brew_date'].max() if not bean_records.empty else "없음"
                
                # 모바일 친화적 카드 디자인
                st.markdown(f"""
                <div class="coffee-card">
                    <h4 style="margin: 0; color: #8B4513; font-size: 1.4rem;">☕ {bean['name']}</h4>
                    <div style="margin: 0.8rem 0;">
                        <p style="margin: 0.3rem 0; color: #666; font-size: 1rem;"><strong>🏪 구매처:</strong> {bean['shop'] or '미입력'}</p>
                        <p style="margin: 0.3rem 0; color: #666; font-size: 1rem;"><strong>🌱 품종:</strong> {bean['variety'] or '미입력'}</p>
                        <p style="margin: 0.3rem 0; color: #666; font-size: 1rem;"><strong>🔥 로스팅:</strong> {bean['roast_date'] or '미입력'}</p>
                        <div style="display: flex; justify-content: space-between; margin-top: 0.8rem;">
                            <span style="color: #8B4513; font-weight: bold;">☕ {brew_count}회 추출</span>
                            <span style="color: #666;">📅 {last_brew}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 버튼들을 2열로 배치
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"🎯 {bean['name']} 추출하기", key=f"brew_{bean['id']}", use_container_width=True):
                        st.session_state.selected_bean_id = bean['id']
                        st.session_state.current_page = f"☕ {bean['name']} 추출하기"
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"delete_bean_{bean['id']}", help=f"{bean['name']} 삭제"):
                        if st.session_state.get(f'confirm_delete_bean_{bean["id"]}', False):
                            delete_bean(bean['id'])
                            # 삭제 확인 상태 초기화
                            if f'confirm_delete_bean_{bean["id"]}' in st.session_state:
                                del st.session_state[f'confirm_delete_bean_{bean["id"]}']
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_bean_{bean["id"]}'] = True
                            st.rerun()  # 상태 변경 후 즉시 rerun
                
                # 삭제 확인 상태일 때 경고 메시지와 취소 버튼 표시
                if st.session_state.get(f'confirm_delete_bean_{bean["id"]}', False):
                    st.warning(f"⚠️ '{bean['name']}'과 관련 추출 기록이 모두 삭제됩니다. 다시 한 번 🗑️ 버튼을 눌러주세요.")
                    if st.button("❌ 취소", key=f"cancel_delete_bean_{bean['id']}", use_container_width=True):
                        del st.session_state[f'confirm_delete_bean_{bean["id"]}']
                        st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)  # 카드 간 간격
        else:
            st.info("아직 등록된 원두가 없습니다. 먼저 원두를 등록해주세요!")
            if st.button("➕ 원두 등록하러 가기", use_container_width=True):
                st.session_state.current_page = "🫘 원두 등록"
                st.rerun()
    
    elif menu == "🫘 원두 등록":
        st.header("🫘 새 원두 등록")
        
        with st.form("bean_form"):
            name = st.text_input("☕ 원두 이름 *", placeholder="예: 콜롬비아 수프리모")
            
            col1, col2 = st.columns(2)
            with col1:
                shop = st.text_input("🏪 구매처", placeholder="예: 스타벅스, 블루보틀 등")
                variety = st.text_input("🌱 품종", placeholder="예: 아라비카, 게이샤 등")
            
            with col2:
                roast_date = st.date_input("🔥 로스팅 날짜", value=None)
            
            notes = st.text_area("📝 메모", placeholder="원두에 대한 특징이나 메모를 적어주세요", height=100)
            
            submitted = st.form_submit_button("💾 원두 등록", use_container_width=True)
            
            if submitted:
                if name:
                    save_bean(name, shop, variety, roast_date, notes)
                else:
                    st.error("원두 이름은 필수입니다!")
    
    elif menu.startswith("☕") and "추출하기" in menu:
        if st.session_state.selected_bean_id:
            bean_info = get_bean_info(st.session_state.selected_bean_id)
            
            if bean_info is not None:
                st.header(f"☕ {bean_info['name']} 추출 기록")
                
                # 원두 정보 표시
                with st.expander("📋 선택된 원두 정보", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**이름:** {bean_info['name']}")
                        st.write(f"**구매처:** {bean_info['shop'] or '미입력'}")
                    with col2:
                        st.write(f"**품종:** {bean_info['variety'] or '미입력'}")
                        st.write(f"**로스팅 날짜:** {bean_info['roast_date'] or '미입력'}")
                    if bean_info['notes']:
                        st.write(f"**메모:** {bean_info['notes']}")
                
                # 커핑 노트 템플릿 (form 밖에서)
                st.markdown("---")
                st.subheader("📝 커핑 노트 템플릿 선택")
                cupping_notes = cupping_tags_selector()
                
                # 추출 기록 폼
                with st.form("brewing_form"):
                    st.subheader("📱 추출 정보")
                    
                    # 모바일 최적화: 세로 배치
                    brew_date = st.date_input("📅 추출 날짜", value=date.today())
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        grind_size = st.number_input("⚙️ 분쇄도 (클릭)", min_value=1, max_value=50, value=24, step=1,
                                                   help="분쇄기 클릭 수 (숫자가 클수록 굵은 분쇄)")
                        coffee_amount = st.number_input("☕ 커피 양 (g)", min_value=0.0, step=0.1, value=20.0)
                    
                    with col2:
                        water_temp = st.selectbox("🌡️ 물 온도 (°C)", 
                                                options=list(range(88, 101)), 
                                                index=2)  # 90도가 디폴트
                        adding_water = st.number_input("💧 첨수 (g)", min_value=0.0, step=1.0, value=100.0, 
                                                     help="추가로 넣을 물의 양")
                    
                    brew_time = st.text_input("⏱️ 총 추출 시간", placeholder="예: 4분 30초")
                    method = st.selectbox("🎯 추출 방법", 
                        ["드립", "프렌치프레스", "에어로프레스", "에스프레소", "콜드브루", "기타"])
                    equipment = st.selectbox("🛠️ 추출 도구", 
                        ["하리오 V60", "에어로프레스", "기타"])
                    
                    # 푸어오버 스케줄 편집
                    st.subheader("🌊 푸어오버 스케줄")
                    
                    # 푸어 단계 추가 버튼 (form 안에서)
                    col_add, col_reset = st.columns([1, 1])
                    with col_add:
                        add_pour = st.form_submit_button("➕ 푸어 단계 추가")
                    with col_reset:
                        reset_schedule = st.form_submit_button("🗑️ 스케줄 초기화")
                    
                    if add_pour:
                        # 마지막 시간을 기준으로 30초 후 시간 계산
                        last_time = st.session_state.pour_schedule[-1]['time']
                        try:
                            if ':' in last_time:
                                minutes, seconds = map(int, last_time.split(':'))
                                total_seconds = minutes * 60 + seconds + 30
                                new_minutes = total_seconds // 60
                                new_seconds = total_seconds % 60
                                new_time = f"{new_minutes}:{new_seconds:02d}"
                            else:
                                new_time = "0:30"
                        except:
                            new_time = "0:30"
                        
                        st.session_state.pour_schedule.append({
                            'water_amount': 60,
                            'time': new_time
                        })
                        st.rerun()
                    
                    if reset_schedule:
                        st.session_state.pour_schedule = [{'water_amount': 40, 'time': '0:00'}]
                        st.rerun()
                    
                    # 각 푸어 단계 편집
                    updated_schedule = []
                    total_pour_water = 0
                    
                    for i, pour in enumerate(st.session_state.pour_schedule):
                        st.write(f"**Pour {i+1}:**")
                        col_water, col_time = st.columns(2)
                        
                        with col_water:
                            pour_water = st.number_input(
                                f"💧 물량 (g)", 
                                min_value=0.0, 
                                step=1.0, 
                                value=float(pour['water_amount']),
                                key=f"form_pour_water_{i}"
                            )
                            total_pour_water += pour_water
                        
                        with col_time:
                            pour_time = st.text_input(
                                f"⏰ 시작 시간", 
                                value=pour['time'],
                                placeholder="예: 0:30",
                                key=f"form_pour_time_{i}"
                            )
                        
                        updated_schedule.append({
                            'water_amount': pour_water,
                            'time': pour_time
                        })
                    
                    # Brewing Ratio 계산 및 표시
                    total_water = total_pour_water + adding_water
                    if coffee_amount > 0:
                        brewing_ratio = total_water / coffee_amount
                        
                        # Brewing Ratio 정보 박스
                        st.info(f"""
                        **📊 Brewing Ratio 정보**
                        - 푸어 물량 합계: {total_pour_water}g
                        - 첨수: {adding_water}g  
                        - 총 물량: {total_water}g
                        - 커피량: {coffee_amount}g
                        - **Brewing Ratio: 1:{brewing_ratio:.1f}**
                        """)
                        
                        # 현재 스케줄 미리보기
                        if updated_schedule:
                            preview_text = " → ".join([f"{pour['water_amount']}g ({pour['time']})" for pour in updated_schedule])
                            st.success(f"**푸어 스케줄:** {preview_text}")
                    
                    st.markdown("---")
                    
                    st.subheader("⭐ 평가 (1-5점)")
                    
                    # 모바일 최적화: 슬라이더들을 세로로 배치
                    taste_score = st.slider("👅 맛", 1, 5, 3)
                    aroma_score = st.slider("👃 향", 1, 5, 3)
                    body_score = st.slider("🫖 바디감", 1, 5, 3)
                    acidity_score = st.slider("🍋 산미", 1, 5, 3)
                    overall_score = st.slider("🏆 전체 만족도", 1, 5, 3)
                    
                    # 테이스팅 노트 (커핑 태그 자동 추가)
                    default_tasting_notes = cupping_notes if cupping_notes else ""
                    tasting_notes = st.text_area("📝 테이스팅 노트", 
                        value=default_tasting_notes,
                        placeholder="위에서 선택한 커핑 태그들이 자동으로 추가됩니다. 추가 설명을 적어주세요!",
                        height=120)
                    
                    improvements = st.text_area("💡 개선사항", 
                        placeholder="다음에 시도해볼 것들을 적어주세요",
                        height=100)
                    
                    # 제출 버튼 (크게)
                    st.markdown("<br>", unsafe_allow_html=True)
                    submitted = st.form_submit_button("💾 추출 기록 저장", use_container_width=True)
                    
                    if submitted:
                        save_brewing_record(
                            st.session_state.selected_bean_id, brew_date, grind_size, 
                            coffee_amount, water_temp, brew_time, method,
                            equipment, adding_water, updated_schedule,
                            taste_score, aroma_score, body_score, acidity_score, 
                            overall_score, tasting_notes, improvements
                        )
                        # 저장 후 초기화 및 홈으로 이동
                        st.session_state.pour_schedule = [{'water_amount': 40, 'time': '0:00'}]
                        st.session_state.selected_cupping_tags = []
                        st.session_state.selected_bean_id = None
                        st.session_state.current_page = "🏠 홈"
                        st.rerun()
    
    elif menu == "📊 추출 기록 보기":
        st.header("📊 추출 기록 보기")
        
        beans_df = get_beans()
        brewing_records_df = get_brewing_records()
        
        if brewing_records_df.empty:
            st.info("🔍 아직 추출 기록이 없습니다.")
            return
        
        # 원두별 필터 (모바일 최적화)
        bean_filter = st.selectbox(
            "🫘 원두 선택",
            ["전체 기록 보기"] + list(beans_df['name'].values) if not beans_df.empty else ["전체 기록 보기"],
            help="특정 원두의 기록만 보고 싶다면 선택하세요"
        )
        
        if bean_filter != "전체 기록 보기":
            selected_bean_id = beans_df[beans_df['name'] == bean_filter]['id'].iloc[0]
            filtered_records = get_brewing_records(selected_bean_id)
        else:
            filtered_records = brewing_records_df
        
        st.write(f"📈 **총 {len(filtered_records)}개의 기록**")
        
        # 기록 표시 (모바일 최적화)
        for _, record in filtered_records.iterrows():
            # Brewing ratio 계산
            total_pour_water = 0
            brewing_ratio_text = ""
            
            if record.get('pour_schedule'):
                try:
                    pour_schedule = json.loads(record['pour_schedule'])
                    total_pour_water = sum([pour['water_amount'] for pour in pour_schedule])
                    total_water = total_pour_water + (record.get('adding_water', 0) or 0)
                    if record['coffee_amount'] > 0:
                        brewing_ratio = total_water / record['coffee_amount']
                        brewing_ratio_text = f" | 📊 1:{brewing_ratio:.1f}"
                except:
                    pass
            
            # 기록 헤더에 삭제 버튼 추가
            col_header, col_delete = st.columns([4, 1])
            
            with col_header:
                expander_title = f"☕ {record['bean_name']} - {record['brew_date']} ⭐{record['overall_score']}/5{brewing_ratio_text}"
            
            with col_delete:
                if st.button("🗑️", key=f"delete_record_{record['id']}", help="이 추출 기록 삭제"):
                    if st.session_state.get(f'confirm_delete_record_{record["id"]}', False):
                        delete_brewing_record(record['id'])
                        st.rerun()
                    else:
                        st.session_state[f'confirm_delete_record_{record["id"]}'] = True
                        st.warning(f"⚠️ 이 추출 기록을 삭제하시겠습니까? 다시 한 번 삭제 버튼을 눌러주세요.")
                        st.rerun()
            
            with st.expander(expander_title):
                # 기본 정보
                st.markdown(f"""
                **📱 추출 정보**
                - 🔥 분쇄도: {record['grind_size']}클릭
                - ☕ 커피량: {record['coffee_amount']}g  
                - 🌡️ 온도: {record['water_temp']}°C
                - ⏱️ 시간: {record['brew_time']}
                - 🎯 방법: {record['method']}
                """)
                
                if record.get('equipment'):
                    st.write(f"🛠️ **도구:** {record['equipment']}")
                if record.get('adding_water'):
                    st.write(f"💧 **첨수:** {record['adding_water']}g")
                
                # Brewing ratio 표시
                if brewing_ratio_text:
                    st.write(f"📊 **{brewing_ratio_text[3:]}**")
                
                # 평가 점수 (이모지로 시각화)
                st.markdown(f"""
                **⭐ 평가 점수**
                - 👅 맛: {'⭐' * record['taste_score']} ({record['taste_score']}/5)
                - 👃 향: {'⭐' * record['aroma_score']} ({record['aroma_score']}/5)  
                - 🫖 바디감: {'⭐' * record['body_score']} ({record['body_score']}/5)
                - 🍋 산미: {'⭐' * record['acidity_score']} ({record['acidity_score']}/5)
                - 🏆 전체: {'⭐' * record['overall_score']} ({record['overall_score']}/5)
                """)
                
                # 푸어오버 스케줄 표시
                if record.get('pour_schedule'):
                    try:
                        pour_schedule = json.loads(record['pour_schedule'])
                        st.write("**🌊 푸어오버 스케줄:**")
                        schedule_text = " → ".join([f"{pour['water_amount']}g ({pour['time']})" for pour in pour_schedule])
                        st.code(schedule_text)
                        st.caption(f"*푸어 총량: {total_pour_water}g*")
                    except:
                        pass
                
                if record['tasting_notes']:
                    st.write(f"**📝 테이스팅 노트:** {record['tasting_notes']}")
                if record['improvements']:
                    st.write(f"**💡 개선사항:** {record['improvements']}")
                
                st.markdown("---")
            
            # 삭제 확인 취소 버튼
            if st.session_state.get(f'confirm_delete_record_{record["id"]}', False):
                if st.button("취소", key=f"cancel_delete_record_{record['id']}"):
                    st.session_state[f'confirm_delete_record_{record["id"]}'] = False
                    st.rerun()
    
    elif menu == "📈 통계":
        st.header("📈 통계 및 분석")
        
        brewing_records_df = get_brewing_records()
        beans_df = get_beans()
        
        if brewing_records_df.empty:
            st.info("📊 통계를 표시할 데이터가 없습니다.")
            return
        
        # 요약 통계 (모바일 최적화)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("☕ 총 추출 횟수", len(brewing_records_df))
            avg_score = brewing_records_df['overall_score'].mean()
            st.metric("⭐ 평균 만족도", f"{avg_score:.1f}/5")
        
        with col2:
            st.metric("🫘 등록된 원두", len(beans_df))
            if len(brewing_records_df) > 0:
                best_bean = brewing_records_df.groupby('bean_name')['overall_score'].mean().idxmax()
                st.metric("🏆 최고 원두", best_bean)
        
        st.markdown("---")
        
        # 차트들 (모바일에서는 세로로 배치)
        # 만족도 분포
        fig = px.histogram(brewing_records_df, x='overall_score', 
                         title='📊 전체 만족도 분포', 
                         nbins=5, range_x=[0.5, 5.5])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 원두별 평균 점수
        bean_scores = brewing_records_df.groupby('bean_name')['overall_score'].mean().reset_index()
        fig = px.bar(bean_scores, x='bean_name', y='overall_score',
                    title='🫘 원두별 평균 만족도')
        fig.update_xaxes(tickangle=45)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 추출 방법별 만족도
        method_scores = brewing_records_df.groupby('method')['overall_score'].mean().reset_index()
        fig = px.bar(method_scores, x='method', y='overall_score',
                    title='🎯 추출 방법별 평균 만족도')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 추출 도구별 만족도
        if 'equipment' in brewing_records_df.columns and brewing_records_df['equipment'].notna().any():
            equipment_scores = brewing_records_df.dropna(subset=['equipment']).groupby('equipment')['overall_score'].mean().reset_index()
            if not equipment_scores.empty:
                fig = px.bar(equipment_scores, x='equipment', y='overall_score',
                            title='🛠️ 추출 도구별 평균 만족도')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # 원두별 추출 횟수
        bean_counts = brewing_records_df['bean_name'].value_counts().reset_index()
        bean_counts.columns = ['bean_name', 'count']
        fig = px.pie(bean_counts, values='count', names='bean_name',
                    title='🫘 원두별 추출 횟수')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 시간별 만족도 추이
        if len(brewing_records_df) > 1:
            brewing_records_df['brew_date'] = pd.to_datetime(brewing_records_df['brew_date'])
            fig = px.line(brewing_records_df, x='brew_date', y='overall_score',
                         color='bean_name', title='📈 시간별 만족도 추이', markers=True)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()