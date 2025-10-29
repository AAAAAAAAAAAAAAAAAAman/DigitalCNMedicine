import os
import json
from openai import OpenAI

origin_prompt = '''
我有一个中医药知识图谱，里面包含的节点（node labels）如下：
Check（检查项目）
Department（科室）
Disease（疾病）
Drug（药物）
Food（食物）
Producer（生产商）
Symptom（症状)
其中疾病节点中包含以下属性，其他节点都仅包含name属性：
【name（疾病名称）,cause（发病原因）,cure_lasttime（治疗周期）,cure_way（治疗方式）,cure_department（治疗科室）,cured_prob（治疗成功率）,
desc（疾病描述）,easy_get（易获得人群）,prevent（预防方法）,get_way（传播途径）,cost_money（治疗费用）】

关系类型(Relationship types)如下（每个关系都包含且仅包含'name'属性）：
acompany_with(某疾病的并发症)
common_drug（某疾病的常用药物）
do_eat（某疾病宜吃什么）
drugs_of（某药物属于某个公司）
has_symptom（有什么症状）
need_check（需要进行什么检查）
no_eat（不能吃，忌口）
recommand_drug（推荐药物）
recommand_eat（推荐食物）
belongs_to（属于哪个科室）

其中的所有三元组逻辑关系如下：
Disease->[acompany_with]->Disease
Disease->[common_drug]->Drug
Producer->[drugs_of]->Drug
Disease->[has_symptom]->Symptom
Disease->[need_check]->Check
Disease->[no_eat]->Food
Disease->[recommand_drug]->Drug
Disease->[recommand_eat]->Food
Disease->[do_eat]->Food
Disease->[belongs_to]->Department

你的任务是根据我给的问题，编写相应的cypher语句，查询neo4j获取结果,编写cypher语句遵循以下逻辑： 逻辑1：如果问题是是否能吃什么食物或者什么药，查询所有能吃的和不能吃的食物和药，而不是仅查询对应的一种。 
逻辑2：如果问能不能干什么事情，是不是谁之类的问题，查询所有能干和不能干的结果，而不是只查询一个结果。 逻辑3：输入的cypher要兼顾图谱种的箭头方向，例如提问“阿莫西林适合治疗什么药物 
逻辑4：编写查询结果的return时，如果查询的是三元组，则将两个节点和关系的name全部返回,格式如下：MATCH (n1)-[r]->(n2) RETURN n1.name, r.name, 
n2.name 逻辑5：当询问的是应该吃或者推荐吃之类的问题时，应该对do_eat和recommand_eat两个关系都进行查询,示例：提问百日咳应该吃什么时，回答： "MATCH (d:Disease{name:'百日咳'})-[
r2:do_eat|recommand_eat]->(f:Food) RETURN d.name, r2.name, f.name" 
逻辑6：用多个语句来实现我要查询的功能，将生成的cypher语句放入一个数组中，最终输出结果以数组形式，例如[cypher语句1，cypher语句2，cypher语句3] 逻辑7：如果用户问的是你好之类的没有查询意义的提问,
那么仅回复一个空的数组:[] 逻辑8：不要输出除最终数组之外的任何内容！不要输出除最终数组之外的任何内容！不要输出除最终数组之外的任何内容！'''


class QwenAPI:
    def __init__(self):
        # 初始化千问大模型的 API Key
        self.API_KEY = os.getenv('DASHSCOPE_API_KEY')

    def qwen_api_kg(self, question):
        # 初始化 OpenAI 客户端
        client = OpenAI(
            api_key=self.API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        # 构造请求参数
        completion = client.chat.completions.create(
            model="qwen-flash",
            messages=[
                {"role": "system", "content": '''
                你是一个Cypher查询语句生成机器人，根据用户要求生成一个包含cypher语句的数组。
                注意：
                1、生成多个cypher语句，使用多个简单的语句来实现我要查询的功能，将生成的cypher语句放入一个数组中，最终输出结果以数组形式，例如[cypher语句1,cypher语句2,cypher语句3]
                2、cured_prob这个字段是治疗成功概率
                3、生成的语句需要是双向的
                !!特别注意：不要输出除最终数组之外的任何内容！不要输出除最终数组之外的任何内容！不要输出除最终数组之外的任何内容！数组里面也不要有任何的例如斜杠,'matchCondition'之类的额外符号!
                正确回答示例1(提问:肺炎杆菌肺炎怎么预防):
                    ["MATCH (d:Disease {name: '肺炎杆菌肺炎'}) RETURN d.prevent"]
                正确回答示例2(提问:得了肺栓塞适合吃什么):
                    ["MATCH (d:Disease {name: '肺栓塞'})-[r:recommand_eat|do_eat]-(f:Food) RETURN d.name AS disease, r.name AS relationship, f.name AS target"]
                正确回答示例3(提问:治疗百日咳要花多少钱):
                    ["MATCH (d:Disease {name: '百日咳'}) RETURN d.cost_money AS cost"]
                正确回答示例4(提问:盐酸舍曲林片可以治疗什么疾病):
                    MATCH (d:Drug {name: '盐酸舍曲林片'})-[r:common_drug|recommand_drug]-(dis:Disease) RETURN d.name AS drug, r.name AS relationship, dis.name AS disease
                '''},
                {"role": "user", "content": origin_prompt},
                {"role": "assistant", "content": "好的，我保证不会输出除了数组之外的任何其他内容。"},
                {"role": "user", "content": question}

            ],
        )
        # 将 JSON 字符串解析为 Python 字典
        completion_data = json.loads(completion.model_dump_json())
        return completion_data["choices"][0]["message"]["content"]