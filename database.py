import sqlite3
import os
from datetime import datetime
import pandas as pd

DATABASE_NAME = "voice_tracker.db"

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)

def create_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_no TEXT NOT NULL UNIQUE,
        project_name TEXT NOT NULL,
        client_name TEXT NOT NULL,
        voice_actor TEXT NOT NULL,
        draft_date TEXT NOT NULL,
        expected_delivery_date TEXT,
        revision_status TEXT DEFAULT '待返稿',
        final_result TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        revision_date TEXT NOT NULL,
        reason TEXT NOT NULL,
        round INTEGER NOT NULL,
        is_urgent INTEGER DEFAULT 0,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS archives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL UNIQUE,
        delivery_file TEXT,
        delivery_version TEXT,
        delivery_date TEXT NOT NULL,
        client_confirmed INTEGER DEFAULT 0,
        client_confirm_date TEXT,
        review_type TEXT,
        review_conclusion TEXT,
        archived_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
    )
    ''')

    cursor.execute("PRAGMA table_info(archives)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'review_type' not in columns:
        cursor.execute('ALTER TABLE archives ADD COLUMN review_type TEXT')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS archive_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL,
        client_name TEXT,
        project_type TEXT,
        delivery_file_rule TEXT,
        delivery_version_rule TEXT,
        review_type TEXT,
        review_conclusion_template TEXT,
        confirm_process TEXT,
        is_default INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

REVIEW_TYPES = ['质量问题', '客户需求变更', '沟通问题', '流程问题', '表现优秀', '其他']

def add_project(project_no, project_name, client_name, voice_actor, 
                draft_date, expected_delivery_date=None, revision_status='待返稿', final_result=''):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO projects (project_no, project_name, client_name, voice_actor, 
                              draft_date, expected_delivery_date, revision_status, final_result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_no, project_name, client_name, voice_actor, 
              draft_date, expected_delivery_date, revision_status, final_result))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"项目编号 {project_no} 已存在")
    finally:
        conn.close()

def update_project(project_id, project_no, project_name, client_name, voice_actor,
                   draft_date, expected_delivery_date=None, revision_status='待返稿', final_result=''):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        UPDATE projects 
        SET project_no=?, project_name=?, client_name=?, voice_actor=?, 
            draft_date=?, expected_delivery_date=?, revision_status=?, final_result=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        ''', (project_no, project_name, client_name, voice_actor,
              draft_date, expected_delivery_date, revision_status, final_result, project_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"项目编号 {project_no} 已存在")
    finally:
        conn.close()

def delete_project(project_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM revisions WHERE project_id=?', (project_id,))
    cursor.execute('DELETE FROM projects WHERE id=?', (project_id,))
    conn.commit()
    conn.close()

def get_all_projects(search_keyword=None, status_filter=None, actor_filter=None):
    conn = create_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT p.*, COUNT(r.id) as revision_count,
           COALESCE(MAX(r.round), 0) as max_round
    FROM projects p
    LEFT JOIN revisions r ON p.id = r.project_id
    WHERE 1=1
    '''
    params = []
    
    if search_keyword:
        query += ''' AND (p.project_no LIKE ? OR p.project_name LIKE ? 
                     OR p.client_name LIKE ? OR p.voice_actor LIKE ?)'''
        like_pattern = f'%{search_keyword}%'
        params.extend([like_pattern, like_pattern, like_pattern, like_pattern])
    
    if status_filter and status_filter != '全部':
        query += ' AND p.revision_status = ?'
        params.append(status_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    query += ' GROUP BY p.id ORDER BY p.updated_at DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_project_by_id(project_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE id=?', (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_revision(project_id, revision_date, reason, round_num, is_urgent=0, description=''):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO revisions (project_id, revision_date, reason, round, is_urgent, description)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (project_id, revision_date, reason, round_num, is_urgent, description))
    conn.commit()
    
    cursor.execute('SELECT COALESCE(MAX(round), 0) FROM revisions WHERE project_id=?', (project_id,))
    max_round = cursor.fetchone()[0]
    
    if max_round >= 1:
        cursor.execute('UPDATE projects SET revision_status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                       ('已返稿', project_id))
    
    conn.commit()
    conn.close()
    return cursor.lastrowid

def update_revision(revision_id, revision_date, reason, round_num, is_urgent=0, description=''):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE revisions 
    SET revision_date=?, reason=?, round=?, is_urgent=?, description=?, created_at=CURRENT_TIMESTAMP
    WHERE id=?
    ''', (revision_date, reason, round_num, is_urgent, description, revision_id))
    conn.commit()
    conn.close()

def delete_revision(revision_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id FROM revisions WHERE id=?', (revision_id,))
    project_id = cursor.fetchone()['project_id']
    
    cursor.execute('DELETE FROM revisions WHERE id=?', (revision_id,))
    
    cursor.execute('SELECT COUNT(*) FROM revisions WHERE project_id=?', (project_id,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        cursor.execute('UPDATE projects SET revision_status=? WHERE id=?', ('待返稿', project_id))
    
    conn.commit()
    conn.close()

def get_revisions_by_project(project_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM revisions WHERE project_id=? ORDER BY round ASC, revision_date ASC', 
                   (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_revision_by_id(revision_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM revisions WHERE id=?', (revision_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_voice_actors():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT voice_actor FROM projects ORDER BY voice_actor')
    rows = cursor.fetchall()
    conn.close()
    return [row['voice_actor'] for row in rows]

def get_revision_statistics():
    conn = create_connection()
    query = '''
    SELECT 
        r.reason,
        COUNT(*) as count,
        COUNT(DISTINCT r.project_id) as project_count
    FROM revisions r
    GROUP BY r.reason
    ORDER BY count DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_voice_actor_statistics():
    conn = create_connection()
    query = '''
    SELECT 
        p.voice_actor,
        COUNT(DISTINCT p.id) as total_projects,
        COUNT(DISTINCT CASE WHEN r.id IS NOT NULL THEN p.id END) as projects_with_revision,
        COUNT(r.id) as total_revisions,
        AVG(r.round) as avg_round,
        SUM(CASE WHEN r.is_urgent = 1 THEN 1 ELSE 0 END) as urgent_count
    FROM projects p
    LEFT JOIN revisions r ON p.id = r.project_id
    GROUP BY p.voice_actor
    ORDER BY total_revisions DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_monthly_statistics():
    conn = create_connection()
    query = '''
    SELECT 
        strftime('%Y-%m', p.draft_date) as month,
        COUNT(DISTINCT p.id) as total_projects,
        COUNT(r.id) as total_revisions
    FROM projects p
    LEFT JOIN revisions r ON p.id = r.project_id
    WHERE p.draft_date IS NOT NULL
    GROUP BY strftime('%Y-%m', p.draft_date)
    ORDER BY month
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_status_statistics():
    conn = create_connection()
    query = '''
    SELECT 
        revision_status,
        COUNT(*) as count
    FROM projects
    GROUP BY revision_status
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_all_clients():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT client_name FROM projects ORDER BY client_name')
    rows = cursor.fetchall()
    conn.close()
    return [row['client_name'] for row in rows]

def calculate_project_risk(project):
    from datetime import datetime, timedelta
    
    risk_score = 0
    risk_factors = []
    
    today = datetime.now().date()
    
    draft_date = None
    if project.get('draft_date'):
        try:
            draft_date = datetime.strptime(project['draft_date'], "%Y-%m-%d").date()
        except:
            pass
    
    expected_date = None
    if project.get('expected_delivery_date'):
        try:
            expected_date = datetime.strptime(project['expected_delivery_date'], "%Y-%m-%d").date()
        except:
            pass
    
    revision_count = project.get('revision_count', 0)
    max_round = project.get('max_round', 0)
    has_urgent = project.get('has_urgent', 0)
    
    if expected_date and project.get('revision_status') not in ['已完成', '已验收']:
        days_left = (expected_date - today).days
        if days_left < 0:
            risk_score += 40
            risk_factors.append(f'已超期{abs(days_left)}天')
        elif days_left <= 2:
            risk_score += 30
            risk_factors.append(f'仅剩{days_left}天交付')
        elif days_left <= 5:
            risk_score += 15
            risk_factors.append(f'仅剩{days_left}天交付')
    
    if max_round >= 3:
        risk_score += 25
        risk_factors.append(f'已返稿{max_round}轮')
    elif max_round >= 2:
        risk_score += 15
        risk_factors.append(f'已返稿{max_round}轮')
    elif max_round >= 1:
        risk_score += 5
    
    if has_urgent:
        risk_score += 20
        risk_factors.append('含加急返稿')
    
    if draft_date and expected_date:
        total_days = (expected_date - draft_date).days
        if total_days > 0 and revision_count > 0:
            avg_days_per_rev = total_days / (revision_count + 1)
            if avg_days_per_rev < 3:
                risk_score += 10
                risk_factors.append('返稿频率高')
    
    if risk_score >= 50:
        risk_level = '高风险'
        risk_color = '#E74C3C'
    elif risk_score >= 25:
        risk_level = '中风险'
        risk_color = '#F39C12'
    else:
        risk_level = '低风险'
        risk_color = '#2ECC71'
    
    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'risk_color': risk_color,
        'risk_factors': risk_factors
    }

def get_projects_with_risk(search_keyword=None, status_filter=None, actor_filter=None, 
                           start_date=None, end_date=None, client_filter=None):
    conn = create_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT p.*, 
           COUNT(r.id) as revision_count,
           COALESCE(MAX(r.round), 0) as max_round,
           COALESCE(MAX(r.is_urgent), 0) as has_urgent
    FROM projects p
    LEFT JOIN revisions r ON p.id = r.project_id
    WHERE 1=1
    '''
    params = []
    
    if search_keyword:
        query += ''' AND (p.project_no LIKE ? OR p.project_name LIKE ? 
                     OR p.client_name LIKE ? OR p.voice_actor LIKE ?)'''
        like_pattern = f'%{search_keyword}%'
        params.extend([like_pattern, like_pattern, like_pattern, like_pattern])
    
    if status_filter and status_filter != '全部':
        query += ' AND p.revision_status = ?'
        params.append(status_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    
    if start_date:
        query += ' AND p.draft_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND p.draft_date <= ?'
        params.append(end_date)
    
    query += ' GROUP BY p.id ORDER BY p.updated_at DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    projects = [dict(row) for row in rows]
    
    for project in projects:
        risk_info = calculate_project_risk(project)
        project.update(risk_info)
    
    return projects

def get_overdue_statistics(start_date=None, end_date=None, client_filter=None, actor_filter=None):
    from datetime import datetime
    conn = create_connection()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    query = '''
    SELECT 
        COUNT(*) as total_projects,
        SUM(CASE WHEN expected_delivery_date < ? AND revision_status NOT IN ('已完成', '已验收') 
                 THEN 1 ELSE 0 END) as overdue_count,
        SUM(CASE WHEN expected_delivery_date >= ? AND revision_status NOT IN ('已完成', '已验收') 
                 THEN 1 ELSE 0 END) as on_time_count,
        SUM(CASE WHEN revision_status IN ('已完成', '已验收') THEN 1 ELSE 0 END) as completed_count
    FROM projects p
    WHERE 1=1
    '''
    params = [today, today]
    
    if start_date:
        query += ' AND p.draft_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND p.draft_date <= ?'
        params.append(end_date)
    
    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_revision_reasons_statistics(start_date=None, end_date=None, client_filter=None, actor_filter=None):
    conn = create_connection()
    
    query = '''
    SELECT 
        r.reason,
        COUNT(*) as count,
        COUNT(DISTINCT r.project_id) as project_count
    FROM revisions r
    INNER JOIN projects p ON r.project_id = p.id
    WHERE 1=1
    '''
    params = []
    
    if start_date:
        query += ' AND r.revision_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND r.revision_date <= ?'
        params.append(end_date)
    
    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    query += ' GROUP BY r.reason ORDER BY count DESC'
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_client_rework_cost_statistics(start_date=None, end_date=None, client_filter=None, actor_filter=None):
    conn = create_connection()
    
    query = '''
    SELECT 
        p.client_name,
        COUNT(DISTINCT p.id) as total_projects,
        COUNT(r.id) as total_revisions,
        COUNT(DISTINCT CASE WHEN r.id IS NOT NULL THEN p.id END) as projects_with_revision,
        COALESCE(AVG(r.round), 0) as avg_round,
        SUM(CASE WHEN r.is_urgent = 1 THEN 1 ELSE 0 END) as urgent_count,
        COALESCE(MAX(r.round), 0) as max_round
    FROM projects p
    LEFT JOIN revisions r ON p.id = r.project_id
    WHERE 1=1
    '''
    params = []
    
    if start_date:
        query += ' AND p.draft_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND p.draft_date <= ?'
        params.append(end_date)
    
    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    query += ' GROUP BY p.client_name ORDER BY total_revisions DESC'
    
    df = pd.read_sql_query(query, conn, params=params)
    
    if not df.empty:
        df['rework_cost_score'] = df['total_revisions'] * 10 + df['urgent_count'] * 5 + df['max_round'] * 8
    
    conn.close()
    return df

def get_risk_level_statistics(start_date=None, end_date=None, client_filter=None, actor_filter=None):
    projects = get_projects_with_risk(
        start_date=start_date,
        end_date=end_date,
        client_filter=client_filter,
        actor_filter=actor_filter
    )
    
    risk_counts = {'高风险': 0, '中风险': 0, '低风险': 0}
    for project in projects:
        level = project.get('risk_level', '低风险')
        if level in risk_counts:
            risk_counts[level] += 1
    
    return pd.DataFrame(list(risk_counts.items()), columns=['risk_level', 'count'])

def get_monthly_trend_statistics(start_date=None, end_date=None, client_filter=None, actor_filter=None):
    from datetime import datetime
    conn = create_connection()
    
    query = '''
    SELECT 
        strftime('%Y-%m', p.draft_date) as month,
        COUNT(DISTINCT p.id) as total_projects,
        COUNT(r.id) as total_revisions,
        SUM(CASE WHEN r.is_urgent = 1 THEN 1 ELSE 0 END) as urgent_count
    FROM projects p
    LEFT JOIN revisions r ON p.id = r.project_id
    WHERE p.draft_date IS NOT NULL
    '''
    params = []
    
    if start_date:
        query += ' AND p.draft_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND p.draft_date <= ?'
        params.append(end_date)
    
    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    query += ' GROUP BY strftime("%Y-%m", p.draft_date) ORDER BY month'
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_urgent_revision_count(start_date=None, end_date=None, client_filter=None, actor_filter=None):
    conn = create_connection()
    
    query = '''
    SELECT COUNT(*) as urgent_count
    FROM revisions r
    INNER JOIN projects p ON r.project_id = p.id
    WHERE r.is_urgent = 1
    '''
    params = []
    
    if start_date:
        query += ' AND r.revision_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND r.revision_date <= ?'
        params.append(end_date)
    
    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    
    return result['urgent_count'] if result else 0

def add_archive(project_id, delivery_file='', delivery_version='', delivery_date='',
                client_confirmed=0, client_confirm_date='', review_type='', review_conclusion=''):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO archives (project_id, delivery_file, delivery_version, delivery_date,
                              client_confirmed, client_confirm_date, review_type, review_conclusion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_id, delivery_file, delivery_version, delivery_date,
              client_confirmed, client_confirm_date, review_type, review_conclusion))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"项目ID {project_id} 已归档")
    finally:
        conn.close()

def update_archive(archive_id, delivery_file='', delivery_version='', delivery_date='',
                   client_confirmed=0, client_confirm_date='', review_type='', review_conclusion=''):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE archives 
    SET delivery_file=?, delivery_version=?, delivery_date=?,
        client_confirmed=?, client_confirm_date=?, review_type=?, review_conclusion=?,
        archived_at=CURRENT_TIMESTAMP
    WHERE id=?
    ''', (delivery_file, delivery_version, delivery_date,
          client_confirmed, client_confirm_date, review_type, review_conclusion, archive_id))
    conn.commit()
    conn.close()

def delete_archive(archive_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM archives WHERE id=?', (archive_id,))
    conn.commit()
    conn.close()

def get_archive_by_id(archive_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM archives WHERE id=?', (archive_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_archive_by_project_id(project_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM archives WHERE project_id=?', (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_archived_projects(client_filter=None, actor_filter=None,
                          start_date=None, end_date=None):
    conn = create_connection()
    cursor = conn.cursor()

    query = '''
    SELECT a.id as archive_id, a.delivery_file, a.delivery_version, a.delivery_date,
           a.client_confirmed, a.client_confirm_date, a.review_type, a.review_conclusion, a.archived_at,
           p.id as project_id, p.project_no, p.project_name, p.client_name, p.voice_actor,
           p.draft_date, p.expected_delivery_date, p.revision_status, p.final_result,
           (SELECT COUNT(*) FROM revisions WHERE project_id = p.id) as revision_count,
           (SELECT COALESCE(MAX(round), 0) FROM revisions WHERE project_id = p.id) as max_round
    FROM archives a
    INNER JOIN projects p ON a.project_id = p.id
    WHERE 1=1
    '''
    params = []

    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)

    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)

    if start_date:
        query += ' AND a.delivery_date >= ?'
        params.append(start_date)

    if end_date:
        query += ' AND a.delivery_date <= ?'
        params.append(end_date)

    query += ' ORDER BY a.archived_at DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_archive_completion_rate(client_filter=None, actor_filter=None,
                                start_date=None, end_date=None):
    conn = create_connection()

    query_total = '''
    SELECT COUNT(*) as total FROM projects p WHERE p.revision_status IN ('已完成', '已验收')
    '''
    params_total = []

    if client_filter and client_filter != '全部':
        query_total += ' AND p.client_name = ?'
        params_total.append(client_filter)
    if actor_filter and actor_filter != '全部':
        query_total += ' AND p.voice_actor = ?'
        params_total.append(actor_filter)
    if start_date:
        query_total += ' AND p.draft_date >= ?'
        params_total.append(start_date)
    if end_date:
        query_total += ' AND p.draft_date <= ?'
        params_total.append(end_date)

    cursor = conn.cursor()
    cursor.execute(query_total, params_total)
    total = cursor.fetchone()[0]

    query_archived = '''
    SELECT COUNT(*) as archived FROM archives a
    INNER JOIN projects p ON a.project_id = p.id
    WHERE 1=1
    '''
    params_archived = []

    if client_filter and client_filter != '全部':
        query_archived += ' AND p.client_name = ?'
        params_archived.append(client_filter)
    if actor_filter and actor_filter != '全部':
        query_archived += ' AND p.voice_actor = ?'
        params_archived.append(actor_filter)
    if start_date:
        query_archived += ' AND a.delivery_date >= ?'
        params_archived.append(start_date)
    if end_date:
        query_archived += ' AND a.delivery_date <= ?'
        params_archived.append(end_date)

    cursor.execute(query_archived, params_archived)
    archived = cursor.fetchone()[0]
    conn.close()

    return {'total': total, 'archived': archived,
            'rate': (archived / total * 100) if total > 0 else 0}

def get_client_confirm_cycle_statistics(client_filter=None, actor_filter=None,
                                        start_date=None, end_date=None):
    conn = create_connection()

    query = '''
    SELECT p.client_name,
           AVG(julianday(a.client_confirm_date) - julianday(a.delivery_date)) as avg_confirm_days,
           MIN(julianday(a.client_confirm_date) - julianday(a.delivery_date)) as min_confirm_days,
           MAX(julianday(a.client_confirm_date) - julianday(a.delivery_date)) as max_confirm_days,
           COUNT(*) as confirmed_count
    FROM archives a
    INNER JOIN projects p ON a.project_id = p.id
    WHERE a.client_confirmed = 1 AND a.client_confirm_date IS NOT NULL
          AND a.delivery_date IS NOT NULL AND a.client_confirm_date >= a.delivery_date
    '''
    params = []

    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    if start_date:
        query += ' AND a.delivery_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND a.delivery_date <= ?'
        params.append(end_date)

    query += ' GROUP BY p.client_name ORDER BY avg_confirm_days DESC'

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_revision_round_distribution(client_filter=None, actor_filter=None,
                                    start_date=None, end_date=None):
    conn = create_connection()

    query = '''
    SELECT 
        COALESCE((SELECT MAX(r2.round) FROM revisions r2 WHERE r2.project_id = p.id), 0) as round_num,
        COUNT(*) as count
    FROM archives a
    INNER JOIN projects p ON a.project_id = p.id
    WHERE 1=1
    '''
    params = []

    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    if start_date:
        query += ' AND a.delivery_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND a.delivery_date <= ?'
        params.append(end_date)

    query += ' GROUP BY round_num ORDER BY round_num'

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_archive_review_summary(client_filter=None, actor_filter=None,
                               start_date=None, end_date=None):
    conn = create_connection()

    query = '''
    SELECT COALESCE(a.review_type, '未分类') as review_type, COUNT(*) as count
    FROM archives a
    INNER JOIN projects p ON a.project_id = p.id
    WHERE 1=1
    '''
    params = []

    if client_filter and client_filter != '全部':
        query += ' AND p.client_name = ?'
        params.append(client_filter)
    if actor_filter and actor_filter != '全部':
        query += ' AND p.voice_actor = ?'
        params.append(actor_filter)
    if start_date:
        query += ' AND a.delivery_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND a.delivery_date <= ?'
        params.append(end_date)

    query += ' GROUP BY a.review_type ORDER BY count DESC'

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def add_archive_template(template_name, client_name='', project_type='',
                         delivery_file_rule='', delivery_version_rule='',
                         review_type='', review_conclusion_template='',
                         confirm_process='', is_default=0):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        if is_default:
            cursor.execute('UPDATE archive_templates SET is_default = 0 WHERE is_default = 1')
        cursor.execute('''
        INSERT INTO archive_templates (template_name, client_name, project_type,
                                       delivery_file_rule, delivery_version_rule,
                                       review_type, review_conclusion_template,
                                       confirm_process, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (template_name, client_name, project_type,
              delivery_file_rule, delivery_version_rule,
              review_type, review_conclusion_template,
              confirm_process, is_default))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"模板名称 {template_name} 已存在")
    finally:
        conn.close()


def update_archive_template(template_id, template_name, client_name='', project_type='',
                            delivery_file_rule='', delivery_version_rule='',
                            review_type='', review_conclusion_template='',
                            confirm_process='', is_default=0):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        if is_default:
            cursor.execute('UPDATE archive_templates SET is_default = 0 WHERE is_default = 1 AND id != ?', (template_id,))
        cursor.execute('''
        UPDATE archive_templates 
        SET template_name=?, client_name=?, project_type=?,
            delivery_file_rule=?, delivery_version_rule=?,
            review_type=?, review_conclusion_template=?,
            confirm_process=?, is_default=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        ''', (template_name, client_name, project_type,
              delivery_file_rule, delivery_version_rule,
              review_type, review_conclusion_template,
              confirm_process, is_default, template_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"模板名称 {template_name} 已存在")
    finally:
        conn.close()


def delete_archive_template(template_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM archive_templates WHERE id=?', (template_id,))
    conn.commit()
    conn.close()


def get_archive_template_by_id(template_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM archive_templates WHERE id=?', (template_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_archive_templates(client_name=None, project_type=None):
    conn = create_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM archive_templates WHERE 1=1'
    params = []
    if client_name and client_name != '全部':
        query += ' AND (client_name = ? OR client_name = "")'
        params.append(client_name)
    if project_type and project_type != '全部':
        query += ' AND (project_type = ? OR project_type = "")'
        params.append(project_type)
    query += ' ORDER BY is_default DESC, updated_at DESC'
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_default_archive_template():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM archive_templates WHERE is_default = 1 LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_archive_templates_by_client(client_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM archive_templates 
    WHERE client_name = ? OR client_name = '' OR is_default = 1
    ORDER BY is_default DESC, 
             CASE WHEN client_name = ? THEN 0 ELSE 1 END,
             updated_at DESC
    ''', (client_name, client_name))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
