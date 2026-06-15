import database
from datetime import datetime, timedelta
import random

def init_test_data():
    database.init_database()
    
    voice_actors = ['张伟', '李娜', '王强', '刘芳', '陈明', '赵丽']
    clients = ['腾讯游戏', '网易云音乐', '喜马拉雅', 'B站', '抖音', '快手', '优酷']
    project_names = [
        '王者荣耀新英雄配音',
        '和平精英赛事宣传',
        '原神角色语音包',
        '有声小说《三体》',
        '品牌广告宣传片',
        '动画片配音',
        '教育课程录制',
        '游戏角色台词',
        '广播剧制作',
        '有声读物《红楼梦》',
        'AI助手语音包',
        '动漫主题曲配音',
        '纪录片旁白',
        '企业宣传片',
        '有声书《百年孤独》'
    ]
    
    reasons = [
        '发音错误', '语调/语气问题', '语速问题', '情感表达不准确',
        '音质/录音问题', '断句/停顿问题', '内容修改', '客户要求调整', '其他'
    ]
    
    today = datetime.now()
    
    projects = []
    for i in range(1, 16):
        project_no = f"VO{2025:04d}{i:03d}"
        project_name = random.choice(project_names)
        client_name = random.choice(clients)
        voice_actor = random.choice(voice_actors)
        draft_date = (today - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d")
        expected_date = (today + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d")
        
        status = random.choice(['待返稿', '已返稿', '已验收', '已完成'])
        final_result = random.choice(['', '通过', '部分通过', '未通过']) if status in ['已验收', '已完成'] else ''
        
        project_id = database.add_project(
            project_no, project_name, client_name, voice_actor,
            draft_date, expected_date, status, final_result
        )
        projects.append(project_id)
        
        if status in ['已返稿', '已验收', '已完成'] and random.random() > 0.3:
            num_revisions = random.randint(1, 4)
            for round_num in range(1, num_revisions + 1):
                rev_date = (datetime.strptime(draft_date, "%Y-%m-%d") + 
                           timedelta(days=random.randint(round_num * 2, round_num * 7))).strftime("%Y-%m-%d")
                reason = random.choice(reasons)
                is_urgent = 1 if random.random() > 0.7 else 0
                description = random.choice([
                    '客户反馈发音不标准，已重新录制',
                    '调整语速和语气，使其更符合角色设定',
                    '修改了部分台词内容，需重新配音',
                    '提高录音质量，降低背景噪音',
                    '根据导演要求调整情感表达',
                    '加急处理，24小时内完成修改'
                ])
                
                database.add_revision(
                    project_id, rev_date, reason, round_num, is_urgent, description
                )
    
    print("测试数据初始化完成！")
    print(f"已创建 {len(projects)} 个项目，包含若干返稿记录。")

if __name__ == "__main__":
    init_test_data()
