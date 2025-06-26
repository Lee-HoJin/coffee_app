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

# 원두 저장
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

# 원두 목록 가져오기
def get_beans():
    conn = sqlite3.connect('coffee_tracker.db')
    df = pd.read_sql_query("SELECT * FROM beans ORDER BY created_date DESC", conn)
    conn.close()
    return df

# 특정 원두의 추출 기록 가져오기
def get_brewing_records(bean_id=None):
    conn = sqlite3.connect('coffee_tracker.db')
    if bean_id:
        query = '''
            SELECT br.*, b.name as bean_name 
            FROM brewing_records br 
            JOIN beans b ON br.bean_id = b.id 
            WHERE br.bean_id = ?
            ORDER BY br.brew_date DESC
        '''
        df = pd.read_sql_query(query, conn, params=(bean_id,))
    else:
        query = '''
            SELECT br.*, b.name as bean_name 
            FROM brewing_records br 
            JOIN beans b ON br.bean_id = b.id 
            ORDER BY br.brew_date DESC
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

# 메인 앱
def main():
    st.set_page_config(page_title="☕ 커피 추출 기록", layout="wide")
    
    # 데이터베이스 초기화
    init_database()
    
    # 세션 상태 초기화
    if 'selected_bean_id' not in st.session_state:
        st.session_state.selected_bean_id = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 홈"
    if 'pour_schedule' not in st.session_state:
        st.session_state.pour_schedule = [{'water_amount': 40, 'time': '0:00'}]
    
    st.title("☕ 커피 추출 기록")
    st.markdown("---")
    
    # 사이드바 메뉴
    st.sidebar.title("메뉴")
    
    # 선택된 원두가 있으면 추출 기록 페이지로 이동 옵션 표시
    menu_options = ["🏠 홈", "🫘 원두 등록", "📊 추출 기록 보기", "📈 통계"]
    if st.session_state.selected_bean_id:
        bean_info = get_bean_info(st.session_state.selected_bean_id)
        if bean_info is not None:
            menu_options.insert(1, f"☕ {bean_info['name']} 추출하기")
    
    menu = st.sidebar.selectbox(
        "원하는 기능을 선택하세요",
        menu_options,
        index=menu_options.index(st.session_state.current_page) if st.session_state.current_page in menu_options else 0
    )
    
    st.session_state.current_page = menu
    
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
            st.subheader("원두를 클릭하여 추출 기록을 시작하세요!")
            
            # 원두 카드들을 3열로 배치
            cols = st.columns(3)
            for idx, (_, bean) in enumerate(beans_df.iterrows()):
                with cols[idx % 3]:
                    # 해당 원두의 추출 횟수 계산
                    bean_records = brewing_records_df[brewing_records_df['bean_id'] == bean['id']]
                    brew_count = len(bean_records)
                    last_brew = bean_records['brew_date'].max() if not bean_records.empty else "없음"
                    
                    with st.container():
                        st.markdown(f"""
                        <div style="
                            padding: 1rem;
                            border: 2px solid #ddd;
                            border-radius: 10px;
                            margin-bottom: 1rem;
                            background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);
                        ">
                            <h4 style="margin: 0; color: #8B4513;">☕ {bean['name']}</h4>
                            <p style="margin: 0.5rem 0; color: #666;"><strong>구매처:</strong> {bean['shop'] or '미입력'}</p>
                            <p style="margin: 0.5rem 0; color: #666;"><strong>품종:</strong> {bean['variety'] or '미입력'}</p>
                            <p style="margin: 0.5rem 0; color: #666;"><strong>로스팅:</strong> {bean['roast_date'] or '미입력'}</p>
                            <p style="margin: 0.5rem 0; color: #666;"><strong>추출 횟수:</strong> {brew_count}회</p>
                            <p style="margin: 0; color: #666;"><strong>마지막 추출:</strong> {last_brew}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"🎯 {bean['name']} 추출하기", key=f"brew_{bean['id']}", use_container_width=True):
                            st.session_state.selected_bean_id = bean['id']
                            st.session_state.current_page = f"☕ {bean['name']} 추출하기"
                            st.rerun()
        else:
            st.info("아직 등록된 원두가 없습니다. 먼저 원두를 등록해주세요!")
            if st.button("➕ 원두 등록하러 가기", use_container_width=True):
                st.session_state.current_page = "🫘 원두 등록"
                st.rerun()
    
    elif menu == "🫘 원두 등록":
        st.header("새 원두 등록")
        
        with st.form("bean_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("원두 이름 *", placeholder="예: 콜롬비아 수프리모")
                shop = st.text_input("구매처", placeholder="예: 스타벅스, 블루보틀 등")
                variety = st.text_input("품종", placeholder="예: 아라비카, 게이샤 등")
            
            with col2:
                roast_date = st.date_input("로스팅 날짜", value=None)
                notes = st.text_area("메모", placeholder="원두에 대한 특징이나 메모를 적어주세요")
            
            submitted = st.form_submit_button("원두 등록")
            
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
                
                # 추출 기록 폼
                with st.form("brewing_form"):
                    st.subheader("추출 정보")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        brew_date = st.date_input("추출 날짜", value=date.today())
                        grind_size = st.number_input("분쇄도 (클릭)", min_value=1, max_value=50, value=24, step=1,
                                                   help="분쇄기 클릭 수 (숫자가 클수록 굵은 분쇄)")
                        coffee_amount = st.number_input("커피 양 (g)", min_value=0.0, step=0.1, value=20.0)
                        adding_water = st.number_input("첨수 (g)", min_value=0.0, step=1.0, value=100.0, 
                                                     help="추가로 넣을 물의 양")
                    
                    with col2:
                        water_temp = st.selectbox("물 온도 (°C)", 
                                                options=list(range(88, 101)), 
                                                index=2)  # 90도가 디폴트
                        brew_time = st.text_input("총 추출 시간", placeholder="예: 4분 30초")
                        method = st.selectbox("추출 방법", 
                            ["드립", "프렌치프레스", "에어로프레스", "에스프레소", "콜드브루", "기타"])
                        equipment = st.selectbox("추출 도구", 
                            ["하리오 V60", "에어로프레스", "기타"])
                    
                    # 푸어오버 스케줄 편집
                    st.subheader("푸어오버 스케줄")
                    
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
                        col_water, col_time = st.columns(2)
                        
                        with col_water:
                            pour_water = st.number_input(
                                f"물량 {i+1} (g)", 
                                min_value=0.0, 
                                step=1.0, 
                                value=float(pour['water_amount']),
                                key=f"form_pour_water_{i}"
                            )
                            total_pour_water += pour_water
                        
                        with col_time:
                            pour_time = st.text_input(
                                f"시작 시간 {i+1}", 
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
                    
                    st.subheader("평가 (1-5점)")
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        taste_score = st.slider("맛", 1, 5, 3)
                        aroma_score = st.slider("향", 1, 5, 3)
                        body_score = st.slider("바디감", 1, 5, 3)
                    
                    with col4:
                        acidity_score = st.slider("산미", 1, 5, 3)
                        overall_score = st.slider("전체 만족도", 1, 5, 3)
                    
                    tasting_notes = st.text_area("테이스팅 노트", 
                        placeholder="단맛, 쓴맛, 과일향, 견과류 등 느낀 맛과 향을 적어주세요")
                    improvements = st.text_area("개선사항", 
                        placeholder="다음에 시도해볼 것들을 적어주세요")
                    
                    submitted = st.form_submit_button("추출 기록 저장", use_container_width=True)
                    
                    if submitted:
                        save_brewing_record(
                            st.session_state.selected_bean_id, brew_date, grind_size, 
                            coffee_amount, water_temp, brew_time, method,
                            equipment, adding_water, updated_schedule,
                            taste_score, aroma_score, body_score, acidity_score, 
                            overall_score, tasting_notes, improvements
                        )
                        # 저장 후 푸어 스케줄 초기화 및 홈으로 이동
                        st.session_state.pour_schedule = [{'water_amount': 40, 'time': '0:00'}]
                        st.session_state.selected_bean_id = None
                        st.session_state.current_page = "🏠 홈"
                        st.rerun()
    
    elif menu == "📊 추출 기록 보기":
        st.header("추출 기록 보기")
        
        beans_df = get_beans()
        brewing_records_df = get_brewing_records()
        
        if brewing_records_df.empty:
            st.info("아직 추출 기록이 없습니다.")
            return
        
        # 원두별 필터
        bean_filter = st.selectbox(
            "원두 선택 (전체 보기 또는 특정 원두)",
            ["전체"] + list(beans_df['name'].values) if not beans_df.empty else ["전체"]
        )
        
        if bean_filter != "전체":
            selected_bean_id = beans_df[beans_df['name'] == bean_filter]['id'].iloc[0]
            filtered_records = get_brewing_records(selected_bean_id)
        else:
            filtered_records = brewing_records_df
        
        # 기록 표시
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
                        brewing_ratio_text = f" | Ratio 1:{brewing_ratio:.1f}"
                except:
                    pass
            
            with st.expander(f"☕ {record['bean_name']} - {record['brew_date']} (만족도: {record['overall_score']}/5{brewing_ratio_text})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**추출 정보**")
                    st.write(f"분쇄도: {record['grind_size']}클릭")
                    st.write(f"커피량: {record['coffee_amount']}g")
                    st.write(f"온도: {record['water_temp']}°C")
                    if record.get('equipment'):
                        st.write(f"도구: {record['equipment']}")
                    if record.get('adding_water'):
                        st.write(f"첨수: {record['adding_water']}g")
                    
                    # Brewing ratio 표시
                    if brewing_ratio_text:
                        st.write(f"**{brewing_ratio_text[3:]}**")  # " | " 제거하고 표시
                
                with col2:
                    st.write("**평가 점수**")
                    st.write(f"맛: {record['taste_score']}/5")
                    st.write(f"향: {record['aroma_score']}/5")
                    st.write(f"바디감: {record['body_score']}/5")
                    st.write(f"산미: {record['acidity_score']}/5")
                
                with col3:
                    st.write("**기타 정보**")
                    st.write(f"추출시간: {record['brew_time']}")
                    st.write(f"추출방법: {record['method']}")
                    st.write(f"전체만족도: {record['overall_score']}/5")
                
                # 푸어오버 스케줄 표시
                if record.get('pour_schedule'):
                    try:
                        pour_schedule = json.loads(record['pour_schedule'])
                        st.write("**푸어오버 스케줄:**")
                        schedule_text = " → ".join([f"{pour['water_amount']}g ({pour['time']})" for pour in pour_schedule])
                        st.write(schedule_text)
                        st.write(f"*푸어 총량: {total_pour_water}g*")
                    except:
                        pass
                
                if record['tasting_notes']:
                    st.write(f"**테이스팅 노트:** {record['tasting_notes']}")
                if record['improvements']:
                    st.write(f"**개선사항:** {record['improvements']}")
    
    elif menu == "📈 통계":
        st.header("통계 및 분석")
        
        brewing_records_df = get_brewing_records()
        beans_df = get_beans()
        
        if brewing_records_df.empty:
            st.info("통계를 표시할 데이터가 없습니다.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 만족도 분포
            fig = px.histogram(brewing_records_df, x='overall_score', 
                             title='전체 만족도 분포', 
                             nbins=5, range_x=[0.5, 5.5])
            st.plotly_chart(fig, use_container_width=True)
            
            # 추출 방법별 만족도
            method_scores = brewing_records_df.groupby('method')['overall_score'].mean().reset_index()
            fig = px.bar(method_scores, x='method', y='overall_score',
                        title='추출 방법별 평균 만족도')
            st.plotly_chart(fig, use_container_width=True)
            
            # 추출 도구별 만족도
            if 'equipment' in brewing_records_df.columns and brewing_records_df['equipment'].notna().any():
                equipment_scores = brewing_records_df.dropna(subset=['equipment']).groupby('equipment')['overall_score'].mean().reset_index()
                if not equipment_scores.empty:
                    fig = px.bar(equipment_scores, x='equipment', y='overall_score',
                                title='추출 도구별 평균 만족도')
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 원두별 평균 점수
            bean_scores = brewing_records_df.groupby('bean_name')['overall_score'].mean().reset_index()
            fig = px.bar(bean_scores, x='bean_name', y='overall_score',
                        title='원두별 평균 만족도')
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            # 원두별 추출 횟수
            bean_counts = brewing_records_df['bean_name'].value_counts().reset_index()
            bean_counts.columns = ['bean_name', 'count']
            fig = px.pie(bean_counts, values='count', names='bean_name',
                        title='원두별 추출 횟수')
            st.plotly_chart(fig, use_container_width=True)
        
        # 시간별 만족도 추이
        if len(brewing_records_df) > 1:
            brewing_records_df['brew_date'] = pd.to_datetime(brewing_records_df['brew_date'])
            fig = px.line(brewing_records_df, x='brew_date', y='overall_score',
                         color='bean_name', title='시간별 만족도 추이', markers=True)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()