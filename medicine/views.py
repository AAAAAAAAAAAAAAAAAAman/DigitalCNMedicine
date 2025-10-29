import requests
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from sentence_transformers import SentenceTransformer, util
from medicine.models import *
from medicine.qs.chatbot_graph import *
import numpy as np
import random
import difflib
from bs4 import BeautifulSoup
from django.http import StreamingHttpResponse
import os
from django.contrib import messages
from medicine.qs.answer_search import *
from medicine.qs.qwen_api import *
from baidusearch.baidusearch import search
'''主页'''
def index(request):
    try:
        print(request.session['status'])
    except Exception:
        request.session['status'] = 0
    return render(request, 'index.html', {'session': request.session})

'''AI问答界面，点击智能推荐后出现的弹窗'''
def internet_search_view(request):
    if request.method == 'POST':
        id = str(request.POST.get('id', '')).strip()
        question_ask = QSHistory.objects.filter(qid=id).values('question').first()
        question = question_ask['question']
        print("搜索问题:  ", question)
        results = search(question)  # 返回10个或更少的结果
        print(results)
        # 初始化 urls 列表
        urls = []

        # 遍历 results 中的每个结果
        for result in results:
            if result['url'].startswith("http"):
                # 提取 title 和 url 并添加到 urls 列表中
                urls.append({
                    "title": result['title'],
                    "url": result['url']
                })
        # 将数据传递给模板
        return render(request, 'internet_search.html', {'urls': urls})
    else:
        return render(request, 'internet_search.html', {'session': request.session})
'''管理员主页'''
def root_index(request):
    try:
        print(request.session['status'])
    except Exception:
        request.session['status'] = 0
    return render(request, 'root_index.html', {'session': request.session})



'''AI问答的核心'''
@require_http_methods(["GET", "POST"])  # 校验用户上传的考官文件是否符合要求
@csrf_exempt
def api_stream_chat_response(request):
    if request.method == 'POST':
        # try:
        data = json.loads(request.body)
        user_qs = data.get('question', '')
        qid = data.get('id')
        # print('qid', qid)
        use_large_model = data.get("use_model", "true").lower() == "true"  # 是否调用大模型
        use_lian_wang = data.get("use_lian_wang", "true").lower() == "true"  # 是否联网搜索
        # print('use_large_model:  ', use_large_model)
        if not use_large_model:
            # 调用大模型能力的逻辑
            if_model = "你选择了不调用大模型"
        else:
            # 不调用大模型能力的逻辑
            if_model = "你选择了调用大模型"
        print(if_model)
        if_lian_wang = ''
        if not use_lian_wang:
            print("你选择了不开启联网搜素")
            lian_wang_result = ''
            if_lian_wang = "否"
            url = ''
            url_title = ''

        else:
            print("你选择了开启联网搜素")
            if_lian_wang = "是"
            results = search(user_qs)  # 返回10个或更少的结果
            url = results[0]['url']  # 第一个链接
            url_title = results[0]['title']  #  第一个链接的标题
            url1 = results[1]['url']
            url1_title = results[1]['title']
            print('url_title:   ', url_title)
            print('url:   ', url)
            # print(extract_text_from_url(user_qs))
            lian_wang_result = extract_text_from_url(url)  #  解析出第一个链接的文本内容并返回作为大模型联网搜索的背景知识
            # lian_wang_result = get_top_relevant_texts(user_qs)  #  这个效果最好最合理，解析多个rul，并将url的内容解析出来，切分后再取相似度最高的5个片段返回，但是语义相似度计算模型加载耗时比较大，还涉及网络问题，因此停用
            print('联网搜索结果',lian_wang_result)
        data = json.loads(request.body)
        # 初始化变量
        full_answer = ""  # 用于存储完整的答案
        cypher_bot = ChatBotGraph()
        total_cypher_answers = cypher_bot.chat_main(user_qs, use_large_model)

        print('cypher查询结果:  ', total_cypher_answers)
        client = OpenAI(
            api_key = os.getenv('DASHSCOPE_API_KEY'),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        def generate(if_lian_wang):
            nonlocal full_answer  # 使用非局部变量存储完整答案
            if if_lian_wang == "是":
                completion = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "user",
                         "content": f"你是一个问答机器人，根据用户问题和参考资料，总结出对应的回答，回答做到逻辑清晰、易于理解。"
                                    f"注意：你会得到两份参考知识，其中一份是从neo4j中查询出的结果，这份作为知识的权威源头，必须完整的展示；另一份是联网搜索的网页结果，作为知识的补充源。而且在回答的时候不要提到参考资料等字样。"
                                    f"给出的参考资料如下："
                                    f"1、neo4j查询结果（权威源,这里的内容必须全部提到）：{total_cypher_answers}；"
                                    f"2、联网搜索结果（补充源，有可能为空）：{lian_wang_result}；在回答的最后附上联网搜索的链接，链接名称1：{url_title}，链接地址1：{url},链接名称2：{url1_title}，链接地址2：{url1},链接直接赋到链接名称中，若为空则不需要展示链接。"
                                    f"请根据用户提问回答"},
                        {"role": "user", "content": user_qs}
                    ],
                    stream=True
                )
            else:
                completion = client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "user",
                         "content": f"你是一个问答机器人，根据用户问题和参考资料，总结出对应的回答，回答做到逻辑清晰、易于理解。"
                                    f"注意：我给你的这份参考知识是neo4j中查询出来的结果，作为知识的权威源头，必须完整的展示。而且在回答的时候不要提到参考资料等字样。"
                                    f"给出的参考资料如下："
                                    f"neo4j查询结果（权威源,这里的内容必须全部提到）：{total_cypher_answers}；"
                                    f"请根据用户提问回答"},
                        {"role": "user", "content": user_qs}
                    ],
                    stream=True
                )
            for chunk in completion:
                if chunk.choices:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:  # 确保有内容
                        full_answer += delta_content  # 收集完整答案
                        yield delta_content.encode('utf-8')  # 返回 UTF-8 编码数据
                        # 流式响应完成后保存完整答案到数据库
            save_to_database(qid, user_qs, full_answer, request.session.get('username'))

        return StreamingHttpResponse(generate(if_lian_wang), content_type='text/plain; charset=utf-8')


# 保存答案到数据库的函数
def save_to_database(qid, question, answer, username):
    try:
        qsht = QSHistory(qid=qid, question=question, ans=answer, satisfy=-1, user=username)
        qsht.save()
        print(f"Saved to database: Question={question}, Answer={answer}")
    except Exception as e:
        print(f"Error saving to database: {e}")


@require_http_methods(["GET", "POST"])  # 校验用户上传的考官文件是否符合要求
@csrf_exempt
def api_stream_test(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')

            client = OpenAI(
                api_key = os.getenv('DASHSCOPE_API_KEY'),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

            def generate():
                completion = client.chat.completions.create(
                    model="qwen-flash",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": question}
                    ],
                    stream=True
                )
                for chunk in completion:
                    if chunk.choices:
                        delta_content = chunk.choices[0].delta.content
                        if delta_content:  # 确保有内容
                            yield delta_content.encode('utf-8')  # 返回 UTF-8 编码数据

            return StreamingHttpResponse(generate(), content_type='text/plain; charset=utf-8')
        except Exception as e:
            return StreamingHttpResponse(str(e), status=500, content_type='text/plain')


@require_http_methods(["GET", "POST"])  # 校验用户上传的考官文件是否符合要求
@csrf_exempt
def stream_test(request):
    return render(request, 'templates/stream_test.html')

def medicine_ai(request):
    try:
        # 检查 session 是否存在 'status' 键
        request.session['status'] = request.session.get('status', 0)
    except Exception:
        request.session['status'] = 0
    qshistory = QSHistory.objects.all().order_by('-id')
    # 将 session.status 传递到模板上下文中
    print('登录状态:', request.session['status'])
    return render(request, 'templates/medicine_ai.html', {
        'session_status': request.session['status']
    })


def root_medicine_ai(request):
    try:
        # 检查 session 是否存在 'status' 键
        request.session['status'] = request.session.get('status', 0)
    except Exception:
        request.session['status'] = 0
    qshistory = QSHistory.objects.all().order_by('-id')
    # 将 session.status 传递到模板上下文中
    print('登录状态:', request.session['status'])
    return render(request, 'templates/root_medicine_ai.html', {
        'session_status': request.session['status']
    })


def single(request):
    # 测试用，大部分功能页面的模板
    return render(request, 'single.html')


def login(request):
    if request.method == "POST":

        user = Users.objects.filter(email=request.POST['email'], password=request.POST['password'])
        if len(user) == 0:
            messages.error(request, '邮箱或密码错误!')
            return render(request, 'login.html')
        request.session['user_id'] = user[0].id
        request.session['username'] = user[0].username
        request.session['group'] = user[0].group
        request.session['status'] = 1
        # print(user[0].username)
        # messages.success(request, '登录成功!')

        if user[0].group == 1:
            return render(request, 'root_index.html', {'session': request.session})
        else:
            return render(request, 'index.html', {'session': request.session})
    else:
        return render(request, 'login.html', {'session': request.session})


def logout(request):
    request.session['status'] = 0
    return render(request, 'index.html', {'session': request.session})


def passageindex(request):
    passages = Article.objects.all()
    return render(request, 'passageindex.html', {'session': request.session, 'passages': passages})


def getpassage(request):
    # print(request.POST.get('passageid'))
    passage = Article.objects.filter(id=request.POST.get('passageid'))
    return render(request, 'passage.html', {'session': request.session, 'passage': passage})




'''主页图谱检索页面的图谱展示'''
def searchresult(request):
    if request.method == 'POST':
        if request.session.get('status', 0) == 0:
            messages.error(request, "请先登录再提问")
            return redirect('/login')  # 重定向到首页或其他页面
        else:
            question = str(request.POST['question'])
            print("question:  ", question)
            status = 0  # 状态为0表示什么都没有找到

            disease_path = "medicine/qs/dict/disease.txt"
            department_path = "medicine/qs/dict/department.txt"
            check_path = "medicine/qs/dict/check.txt"
            drug_path = "medicine/qs/dict/drug.txt"
            food_path = "medicine/qs/dict/food.txt"
            symptom_path = "medicine/qs/dict/symptom.txt"
            # 打开文件并遍历每一行
            best_similarity = 0
            node_name = ""
            with open(disease_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
                for line in file:
                    # 移除行尾的换行符（如果有的话）
                    line = line.strip()
                    similarity = calculate_similarity(line, question)
                    # 检查这行内容是否包含在string变量中
                    if best_similarity < similarity:
                        best_similarity = similarity
                        node_name = line
            with open(department_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
                for line in file:
                    # 移除行尾的换行符（如果有的话）
                    line = line.strip()
                    similarity = calculate_similarity(line, question)
                    # 检查这行内容是否包含在string变量中
                    if best_similarity < similarity:
                        best_similarity = similarity
                        node_name = line
            with open(check_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
                for line in file:
                    # 移除行尾的换行符（如果有的话）
                    line = line.strip()
                    similarity = calculate_similarity(line, question)
                    # 检查这行内容是否包含在string变量中
                    if best_similarity < similarity:
                        best_similarity = similarity
                        node_name = line
            with open(food_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
                for line in file:
                    # 移除行尾的换行符（如果有的话）
                    line = line.strip()
                    similarity = calculate_similarity(line, question)
                    # 检查这行内容是否包含在string变量中
                    if best_similarity < similarity:
                        best_similarity = similarity
                        node_name = line
            with open(symptom_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
                for line in file:
                    # 移除行尾的换行符（如果有的话）
                    line = line.strip()
                    similarity = calculate_similarity(line, question)
                    # 检查这行内容是否包含在string变量中
                    if best_similarity < similarity:
                        best_similarity = similarity
                        node_name = line
            with open(drug_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
                for line in file:
                    # 移除行尾的换行符（如果有的话）
                    line = line.strip()
                    similarity = calculate_similarity(line, question)
                    # 检查这行内容是否包含在string变量中
                    if best_similarity < similarity:
                        best_similarity = similarity
                        node_name = line
            print('node_name', node_name)
            print("best_similarity: ", best_similarity)

            kg_result = get_kg_data(node_name)
            # print(kg_result)
            if node_name:
                neonum = 1
            else:
                neonum = 0
            print(kg_result)
            print('neonum', neonum)
            return render(request, 'templates/show_neo4_jsearchresult.html',
                          {'session': request.session, 'question': question,
                           'kg_data': kg_result, 'neonum': neonum})
    else:
        return render(request, 'templates/show_neo4_jsearchresult.html', {'session': request.session})

'''AI问答页面右侧的图谱展示'''
def model_kg(request):
    if request.method == 'POST':
        id = str(request.POST.get('id', '')).strip()
        question_ask = QSHistory.objects.filter(qid=id).values('question').first()
        question = question_ask['question']
        print("question:  ", question)
        status = 0  # 状态为0表示什么都没有找到

        disease_path = "medicine/qs/dict/disease.txt"
        department_path = "medicine/qs/dict/department.txt"
        check_path = "medicine/qs/dict/check.txt"
        drug_path = "medicine/qs/dict/drug.txt"
        food_path = "medicine/qs/dict/food.txt"
        symptom_path = "medicine/qs/dict/symptom.txt"
        # 打开文件并遍历每一行
        best_similarity = 0
        node_name = ""
        with open(disease_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
            for line in file:
                # 移除行尾的换行符（如果有的话）
                line = line.strip()
                similarity = calculate_similarity(line, question)
                # 检查这行内容是否包含在string变量中
                if best_similarity < similarity:
                    best_similarity = similarity
                    node_name = line
        with open(department_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
            for line in file:
                # 移除行尾的换行符（如果有的话）
                line = line.strip()
                similarity = calculate_similarity(line, question)
                # 检查这行内容是否包含在string变量中
                if best_similarity < similarity:
                    best_similarity = similarity
                    node_name = line
        with open(check_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
            for line in file:
                # 移除行尾的换行符（如果有的话）
                line = line.strip()
                similarity = calculate_similarity(line, question)
                # 检查这行内容是否包含在string变量中
                if best_similarity < similarity:
                    best_similarity = similarity
                    node_name = line
        with open(food_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
            for line in file:
                # 移除行尾的换行符（如果有的话）
                line = line.strip()
                similarity = calculate_similarity(line, question)
                # 检查这行内容是否包含在string变量中
                if best_similarity < similarity:
                    best_similarity = similarity
                    node_name = line
        with open(symptom_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
            for line in file:
                # 移除行尾的换行符（如果有的话）
                line = line.strip()
                similarity = calculate_similarity(line, question)
                # 检查这行内容是否包含在string变量中
                if best_similarity < similarity:
                    best_similarity = similarity
                    node_name = line
        with open(drug_path, 'r', encoding='utf-8') as file:  # 假设你的文件是utf-8编码，如果不是请修改
            for line in file:
                # 移除行尾的换行符（如果有的话）
                line = line.strip()
                similarity = calculate_similarity(line, question)
                # 检查这行内容是否包含在string变量中
                if best_similarity < similarity:
                    best_similarity = similarity
                    node_name = line
        print('node_name', node_name)
        print("best_similarity: ", best_similarity)
        kg_result = get_kg_data(node_name)
        # print(kg_result)
        if node_name:
            neonum = 1
        else:
            neonum = 0
        print(kg_result)
        print('neonum', neonum)
        return render(request, 'model_kg.html',
                      {'session': request.session, 'question': question,
                       'kg_data': kg_result, 'neonum': neonum})
    else:
        return render(request, 'model_kg.html', {'session': request.session})


'''查询neo4j知识图谱并将查询结果格式化为适合echarts使用的格式'''
def get_kg_data(name):
    node_name = []
    kg_re = []
    print("name: ", name)

    # 修改 Cypher 查询以获取节点类型
    cypher_query = f"""
    MATCH (n)-[r1]->(s)
    WHERE n.name = '{name}' OR s.name = '{name}'
    RETURN n.name, TYPE(r1), s.name, LABELS(n) AS n_labels, LABELS(s) AS s_labels
    """

    text = []
    answer_searcher  = AnswerSearcher()
    result = answer_searcher.run(cypher_query)

    nodes = {}  # 用于存储节点及其类型
    for temp in result:

        re = {
            "source": temp["n.name"],
            "target": temp["s.name"],
            "name": temp["TYPE(r1)"],
            "source_type": temp["n_labels"],  # 添加源节点类型
            "target_type": temp["s_labels"]   # 添加目标节点类型
        }
        kg_re.append(re)
        if temp["n.name"] not in nodes:
            nodes[temp["n.name"]] = temp["n_labels"]
        if temp["s.name"] not in nodes:
            nodes[temp["s.name"]] = temp["s_labels"]
        node_name.append(temp["n.name"])
        node_name.append(temp["s.name"])
    final_node_name = list(set(node_name))
    total = []
    nodes = [{key: value[0]} for key, value in nodes.items()]
    print('nodes2',nodes)
    # 类别映射
    category_mapping = {
        "Disease": 0,
        "Department": 1,
        "Symptom": 2,
        "Check": 3,
        "Drug": 4,
        "Food": 5
    }

    # 转换数据
    formatted_data = []
    for item in nodes:
        for name, category in item.items():
            formatted_data.append({
                "name": name,
                "des": 70,  # 固定值示例
                "symbolSize": 70,  # 固定值示例
                "category": category_mapping[category],  # 根据类别映射
                "url": ""  # 如果有链接，可以填充
            })
    total.append(formatted_data)
    total.append(kg_re)

    return total



def qs(request):
    qshistory = QSHistory.objects.all().order_by('-id')
    return render(request, 'qs.html', {'session': request.session, 'qshistory': qshistory})

'''点赞点踩'''
def submitsatisfaction(request):
    if request.method == 'POST':
        answer_id = request.POST.get('id')
        satisfaction = request.POST.get('satis')
        print(f"Answer ID: {answer_id}, Satisfaction: {satisfaction}")
        id1 = request.POST.get('id')
        satis = request.POST.get('satis')
        QSHistory.objects.filter(qid=answer_id).update(satisfy=satisfaction)
    # qshistory = QSHistory.objects.all().order_by('-id')
    # return render(request, 'qs.html', {'session': request.session, 'qshistory': qshistory})
    return JsonResponse({"message": "Satisfaction updated successfully!"})



'''解析url并返回页面的文本内容'''
def extract_text_from_url(url):
    # 发送HTTP请求获取网页内容
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36"
    }
    # print('extract_text_from_url')
    response = requests.get(url, headers=headers)

    # 确保请求成功
    if response.status_code != 200:
        print(f"无法获取网页: {response.status_code}")
        return None

    # 解析HTML内容
    soup = BeautifulSoup(response.text, 'html.parser')

    # 提取所有可见文本，并去除多余的空白
    for script in soup(["script", "style"]):  # 移除JavaScript和CSS
        script.decompose()

    text = soup.get_text()
    lines = [line.strip() for line in text.splitlines()]  # 去除行首尾空白
    chunks = [phrase.strip() for line in lines for phrase in line.split("  ") if phrase]  # 去除多余空格
    text = '\n'.join(chunk for chunk in chunks if chunk)  # 合并非空段落
    return text




'''传入用户提问，使用百度搜索引擎获得多个url，解析这些url的文本，将文本切分成块，调用预训练模型返回与用户问题相似度最高的5个文本块————未启用'''
# 主函数：获取最相关的 5 个文本片段
def get_top_relevant_texts(query, num_results=5, top_n=5):
    # 获取百度搜索结果
    search_results = search_baidu(query)[:num_results]
    search_results = filter_valid_urls(search_results)
    if not search_results:
        print("未找到任何搜索结果")
        return []

    all_texts = []
    url_mapping = {}  # 用于记录每个文本片段对应的 URL
    # 提取每个网页的文本并分段
    for result in search_results:
        url = result['url']
        print(f"正在解析: {url}")
        full_text = extract_text_from_url(url)
        if full_text:
            # 按每 300 个字符切分文本
            chunk_size = 300
            chunks = [full_text[i:i + chunk_size] for i in range(0, len(full_text), chunk_size)]

            # 遍历切分后的文本块
            for chunk in chunks:
                if len(chunk.strip()) > 10:  # 过滤掉过短的片段
                    all_texts.append(chunk.strip())
                    url_mapping[chunk.strip()] = url
    if not all_texts:
        print("未能提取到任何有效文本")
        return []
    # 加载预训练模型
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    # 计算相似度
    similarities = calculate_similarity2(query, all_texts, model)
    # 排序并获取前 top_n 个结果
    top_indices = np.argsort(similarities)[-top_n:][::-1]
    top_texts = [(all_texts[i], similarities[i], url_mapping[all_texts[i]]) for i in top_indices]

    return top_texts


# 使用difflib计算文本相似度
def calculate_similarity(text1, text2):
    seq = difflib.SequenceMatcher(None, text1, text2)
    similarity_ratio = seq.ratio()
    return similarity_ratio


# 计算文本相似度的函数
def calculate_similarity2(query, texts, model):
    query_embedding = model.encode(query, convert_to_tensor=True)
    text_embeddings = model.encode(texts, convert_to_tensor=True)
    cos_scores = util.cos_sim(query_embedding, text_embeddings)[0]
    return cos_scores.cpu().numpy()


# 百度搜索结果的函数
def search_baidu(query):
    from baidusearch.baidusearch import search
    results = search(query)  # 返回最多 10 个结果
    return results
def filter_valid_urls(results):
    """过滤掉无效的 URL，只保留以 http 或 https 开头的 URL"""
    return [result for result in results if result['url'].startswith(('http://', 'https://'))]




def sendemail(request):
    if request.method == 'POST':
        # sendemail()
        messages.success(request, '发送成功！')
    return render(request, 'index.html', {'session': request.session})


def subscribe(request):
    if request.method == 'POST':
        # subscribe()
        messages.success(request, '订阅成功！')
    return render(request, 'index.html', {'session': request.session})


def register(request):
    if request.method == 'POST':
        hasReg = Users.objects.filter(email=request.POST['email'])
        if len(hasReg) > 0:
            messages.error(request, '当前邮箱已有人注册！请检查是否已注册或换个邮箱再试试')
        else:
            user = Users(email=request.POST['email'], password=request.POST['password'], username=request.POST['name'],
                         group=0)
            user.save()
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['group'] = user.group
            request.session['status'] = 1
            messages.success(request, '注册成功！已为您自动登录')
            return render(request, 'index.html', {'session': request.session})

    return render(request, 'register.html', {'session': request.session})


def recommend(request):
    id1 = random.choice(range(1, 1000))
    a = BasicData.objects.filter(id=id1)
    return render(request, 'recommend.html', {'session': request.session, 'a0': a})


def model_kg_test(request):
    node_name = '百日咳'
    print('node_name', node_name)
    kg_result = get_kg_data(node_name)
    # print(kg_result)
    if node_name:
        neonum = 1
    else:
        neonum = 0
    print(kg_result[0])
    print('neonum', neonum)
    return render(request, 'model_kg.html',
                  {'session': request.session,
                   'kg_data': kg_result, 'neonum': neonum})
