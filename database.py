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

    conn.commit()
    conn.close()

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
