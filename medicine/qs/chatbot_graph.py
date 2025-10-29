import ast

from medicine.qs.question_classifier import *
from medicine.qs.question_parser import *
from medicine.qs.answer_search import *
from medicine.qs.qwen_api import *
'''问答类'''


class ChatBotGraph:
    def __init__(self):

        self.searcher = AnswerSearcher()

    def chat_main(self, question,use_large_model):
        if not use_large_model:
            answer = ''
            classifier = QuestionClassifier()
            parser = QuestionPaser()
            res_classify = classifier.classify(question)
            print("res_classify", res_classify)
            if not res_classify:
                return answer

            res_sql = parser.parser_main(res_classify)
            final_answers = self.searcher.search_main(res_sql)
            print("final_answers", final_answers)
            if not final_answers:
                return answer
            else:
                return '\n'.join(final_answers)
        else:
            model_api = QwenAPI()
            sql = model_api.qwen_api_kg(question)
            # 去除开头和结尾的```cypher```
            cleaned_sql = sql.replace("```cypher", "").replace("```", "").strip()
            print('大模型生成的格式优化之后的cypher语句:   ',cleaned_sql)

            try:
                # 将查询结果转变成数组
                cleaned_sql_list = ast.literal_eval(cleaned_sql)
                total_cypher_answers = ''
                for one in cleaned_sql_list:
                    # 打印检查
                    # print("Cleaned one SQL queries:", one)
                    try:
                        final_answers = self.searcher.run(one)  # 尝试执行查询
                    except Exception as e:
                        print(f"在进行neo4j查询时发生错误： '{one}': {e}")
                        final_answers = []  # 如果出错，给 final_answers 赋空列表
                    # print('Cypher语句的查询结果：',final_answers)
                    final_list = []
                    for record in final_answers:
                        # 提取记录中的所有字段
                        fields = list(record.values())  # 获取记录中的所有字段值
                        # 假设每个记录包含1个元素
                        if len(fields) == 1:
                            # 格式化输出：根据顺序输出
                            one = f"{fields[0]}"
                            final_list.append(one)
                        # 假设每个记录包含3个元素，按顺序排列成三元组
                        if len(fields) == 3:
                            # 格式化输出：根据顺序输出
                            one = f"{fields[0]} - {fields[1]} - {fields[2]}"
                            final_list.append(one)
                            # 处理其他字段数目的情况
                        elif len(fields) > 1:
                            # 你可以根据实际需要，格式化所有字段值，例如：
                            one = " - ".join(str(field) for field in fields)
                            final_list.append(one)
                    if final_list:
                        str_answers = str(final_list)
                        total_cypher_answers += str_answers
                return total_cypher_answers

            except Exception as e:
                print(f"Error parsing cleaned_sql: {e}")


if __name__ == '__main__':
    handler = ChatBotGraph()
    while 1:
        question = input('用户:')
        answer = handler.chat_main(question)
        print('BOT:', answer)
