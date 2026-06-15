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

    review_conclusions = [
        ('表现优秀', '项目顺利交付，客户满意度高'),
        ('质量问题', '返稿主要因发音问题，需加强审听'),
        ('客户需求变更', '客户要求频繁变更导致返稿'),
        ('表现优秀', '配音员表现优异，一次通过'),
        ('质量问题', '音质问题导致多次返稿'),
        ('沟通问题', '沟通不畅导致返稿增加'),
        ('流程问题', '加急项目处理得当，按时交付'),
        ('流程问题', '客户内部流程变化导致延期确认'),
    ]

    archive_count = 0
    for project_id in projects:
        project = database.get_project_by_id(project_id)
        if project and project['revision_status'] in ('已完成', '已验收'):
            draft_dt = datetime.strptime(project['draft_date'], "%Y-%m-%d")
            delivery_date = (draft_dt + timedelta(days=random.randint(5, 20))).strftime("%Y-%m-%d")
            client_confirmed = 1 if random.random() > 0.3 else 0
            if client_confirmed:
                confirm_offset = random.randint(1, 7)
                client_confirm_date = (datetime.strptime(delivery_date, "%Y-%m-%d") + timedelta(days=confirm_offset)).strftime("%Y-%m-%d")
            else:
                client_confirm_date = ''
            version = f"v{random.randint(1, 3)}.{random.randint(0, 5)}"
            delivery_files = random.choice([
                'final_mix.wav', 'final_v2.mp3', 'delivery_master.wav',
                'final_stereo.wav', 'complete_pack.zip', 'final_delivery.wav'
            ])
            review_type, review_conclusion = random.choice(review_conclusions)

            database.add_archive(
                project_id=project_id,
                delivery_file=delivery_files,
                delivery_version=version,
                delivery_date=delivery_date,
                client_confirmed=client_confirmed,
                client_confirm_date=client_confirm_date,
                review_type=review_type,
                review_conclusion=review_conclusion
            )
            archive_count += 1

    templates = [
        {
            'template_name': '通用标准模板',
            'client_name': '',
            'project_type': '',
            'delivery_file_rule': '{客户名称}_{项目编号}_final.wav',
            'delivery_version_rule': 'v1.0',
            'review_type': '',
            'review_conclusion_template': '项目{项目名称}已完成交付，整体质量良好。',
            'confirm_process': '1.初审→2.客户试听→3.修改→4.终验',
            'is_default': 1
        },
        {
            'template_name': '腾讯游戏专属模板',
            'client_name': '腾讯游戏',
            'project_type': '游戏配音',
            'delivery_file_rule': 'Tencent_{项目编号}_{项目名称}_v{版本}.wav',
            'delivery_version_rule': 'final',
            'review_type': '质量问题',
            'review_conclusion_template': '腾讯游戏项目{项目名称}交付完成，需关注发音准确性。',
            'confirm_process': '1.录音师审听→2.导演审核→3.腾讯QA验收→4.最终交付',
            'is_default': 0
        },
        {
            'template_name': '喜马拉雅有声书模板',
            'client_name': '喜马拉雅',
            'project_type': '有声书',
            'delivery_file_rule': 'Ximalaya_{项目编号}_Chapter{章节}_final.mp3',
            'delivery_version_rule': 'v2.0',
            'review_type': '表现优秀',
            'review_conclusion_template': '喜马拉雅项目{项目名称}交付顺利，客户满意度高。',
            'confirm_process': '1.主播录制→2.后期制作→3.编辑审核→4.平台上架',
            'is_default': 0
        },
        {
            'template_name': '广告配音模板',
            'client_name': '',
            'project_type': '广告配音',
            'delivery_file_rule': 'AD_{客户名称}_{日期}_{项目编号}.wav',
            'delivery_version_rule': 'v1.0',
            'review_type': '客户需求变更',
            'review_conclusion_template': '广告项目{项目名称}已完成，需注意客户需求变更频率。',
            'confirm_process': '1.初配→2.客户反馈→3.修改→4.终审',
            'is_default': 0
        },
        {
            'template_name': 'B站二次元模板',
            'client_name': 'B站',
            'project_type': '动漫配音',
            'delivery_file_rule': 'Bilibili_{项目名称}_EP{集数}_final.wav',
            'delivery_version_rule': 'v1.5',
            'review_type': '表现优秀',
            'review_conclusion_template': 'B站动漫项目{项目名称}配音完成，角色表现力强。',
            'confirm_process': '1.试音→2.导演确认→3.正片录制→4.后期混音→5.交付',
            'is_default': 0
        }
    ]

    for tpl in templates:
        try:
            database.add_archive_template(**tpl)
        except ValueError:
            pass

    print("测试数据初始化完成！")
    print(f"已创建 {len(projects)} 个项目，包含若干返稿记录。")
    print(f"已归档 {archive_count} 个已完成/已验收项目。")
    print(f"已创建 {len(templates)} 个归档模板。")

if __name__ == "__main__":
    init_test_data()
