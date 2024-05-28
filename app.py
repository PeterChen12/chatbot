import os
from openai import OpenAI
import csv
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_file

# 从 .env 文件加载环境变量
load_dotenv()

# 从环境变量中获取 API 密钥
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

app = Flask(__name__, static_folder='static')

# 与 GPT-4 进行交互的函数
def chat_with_gpt4(messages):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages
    )
    return response.choices[0].message.content.strip()

def extract_information_from_text(conversation, prompt):
    conversation.append({"role": "user", "content": prompt})
    response = chat_with_gpt4(conversation)
    conversation.append({"role": "assistant", "content": response})
    return response

# 根据用户信息推荐产品的函数
def suggest_product(user_info):
    if user_info['household_size'] >= 3:
        size = 'Family Size'
    else:
        size = 'Single Serving'
    
    preferred_color = user_info['preferred_color']
    for product in products:
        if size in product['Name'] and preferred_color in product['Name']:
            return product

# 生成最终推荐消息的函数
def generate_suggestion_message(user_info, product):
    prompt = (
        f"Create a suggestion message based on the following user information and product details:\n"
        f"User Information: {user_info}\n"
        f"Product: {product}\n"
        f"Also, include the coupon/promo code: MEMORIAL20"
    )
    conversation = [
        {"role": "system", "content": "You are a customer service representative for nutr."},
        {"role": "user", "content": prompt}
    ]
    response = chat_with_gpt4(conversation)
    return response

# 初始化对话
conversation = [
    {"role": "system", "content": "You are a friendly customer service representative for nutr. Your task is to get the customers interest in our products and acquire their information on household size, favorite flavor, favorite base, preferred color (out of white and black), and the customer's personal information (email or phone number) and suggest a product from our catalog. Don't ask more than one question at a time. Give promo code: MEMORIAL20 when prompted or after 12 message exchanges."}
]

# 用户信息
user_info = {}

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/<path:filename>')
def send_file_to_client(filename):
    try:
        return send_file(filename)
    except Exception as e:
        return str(e), 404

@app.route('/chat', methods=['POST'])
def chat():
    global conversation, user_info
    user_message = request.json['message']
    conversation.append({"role": "user", "content": user_message})
    bot_response = chat_with_gpt4(conversation)
    conversation.append({"role": "assistant", "content": bot_response})

    # 收集用户信息
    if 'household_size' not in user_info:
        if 'number of people in your household' in user_message.lower():
            user_info['household_size'] = int(user_message.split()[-1])
    elif 'favorite_flavor' not in user_info:
        if any(flavor in user_message.lower() for flavor in ['tumeric', 'vanilla', 'chocolate', 'strawberry', 'matcha']):
            user_info['favorite_flavor'] = user_message.split()[-1]
    elif 'favorite_base' not in user_info:
        if any(base in user_message.lower() for base in ['almond', 'hemp', 'cashew', 'oats']):
            user_info['favorite_base'] = user_message.split()[-1]
    elif 'preferred_color' not in user_info:
        if 'white' in user_message.lower() or 'black' in user_message.lower():
            user_info['preferred_color'] = user_message.split()[-1]
    elif 'email' not in user_info and 'phone number' not in user_info:
        if 'email' in user_message.lower():
            user_info['email'] = user_message.split()[-1]
        elif 'phone number' in user_message.lower():
            user_info['phone_number'] = user_message.split()[-1]

    # 检查并保存用户信息
    required_keys = ['household_size', 'favorite_flavor', 'favorite_base', 'preferred_color', 'email', 'phone_number']
    collected_keys = [key for key in required_keys if key in user_info]
    if len(collected_keys) >= 2:
        save_user_info_to_csv(user_info)

    # 提供产品建议
    if all(key in user_info for key in ['household_size', 'favorite_flavor', 'favorite_base', 'preferred_color']):
        product = suggest_product(user_info)
        response_message = generate_suggestion_message(user_info, product)
        
        user_info = {}  # 重置用户信息
    else:
        response_message = bot_response
    
    return jsonify({'message': response_message})

# 新增的对接”公司“路由，可以对接不同的公司，不同的提示词，等等
@app.route('/chat/<company>', methods=['POST'])
def custom_chat(company):
    global conversation, user_info
    user_message = request.json['message']
    conversation.append({"role": "user", "content": user_message})
    
    # 读取请求公司的特定公司的提示词
    prompt_path = os.path.join('prompts', company, 'prompt.txt')
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r') as file:
            company_prompt = file.read().strip()
    else:
        #没有读取到指定公司的全局通用提示词
        company_prompt = "You are a customer service representative."

    conversation[0] = {"role": "system", "content": company_prompt}
    
    bot_response = chat_with_gpt4(conversation)
    conversation.append({"role": "assistant", "content": bot_response})

    # 收集用户信息
    if 'household_size' not in user_info:
        if 'number of people in your household' in user_message.lower():
            user_info['household_size'] = int(user_message.split()[-1])
    elif 'favorite_flavor' not in user_info:
        if any(flavor in user_message.lower() for flavor in ['tumeric', 'vanilla', 'chocolate', 'strawberry', 'matcha']):
            user_info['favorite_flavor'] = user_message.split()[-1]
    elif 'favorite_base' not in user_info:
        if any(base in user_message.lower() for base in ['almond', 'hemp', 'cashew', 'oats']):
            user_info['favorite_base'] = user_message.split()[-1]
    elif 'preferred_color' not in user_info:
        if 'white' in user_message.lower() or 'black' in user_message.lower():
            user_info['preferred_color'] = user_message.split()[-1]
    elif 'email' not in user_info and 'phone number' not in user_info:
        if 'email' in user_message.lower():
            user_info['email'] = user_message.split()[-1]
        elif 'phone number' in user_message.lower():
            user_info['phone_number'] = user_message.split()[-1]

    # 检查并保存用户信息
    required_keys = ['household_size', 'favorite_flavor', 'favorite_base', 'preferred_color', 'email', 'phone_number']
    collected_keys = [key for key in required_keys if key in user_info]
    if len(collected_keys) >= 2:
        save_user_info_to_csv(user_info)

    # 提供产品建议
    if all(key in user_info for key in ['household_size', 'favorite_flavor', 'favorite_base', 'preferred_color']):
        product = suggest_product(user_info)
        response_message = generate_suggestion_message(user_info, product)
        
        user_info = {}  # 重置用户信息
    else:
        response_message = bot_response
    
    return jsonify({'message': response_message})

# 将用户信息保存到 CSV 文件的函数
def save_user_info_to_csv(user_info):
    file_exists = os.path.isfile('user_info.csv')
    with open('user_info.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Household Size", "Favorite Flavor", "Favorite Base", "Preferred Color", "Email", "Phone Number"])
        writer.writerow([
            user_info.get('household_size', '未提供'),
            user_info.get('favorite_flavor', '未提供'),
            user_info.get('favorite_base', '未提供'),
            user_info.get('preferred_color', '未提供'),
            user_info.get('email', '未提供'),
            user_info.get('phone_number', '未提供')
        ])
    print("用户信息已成功存储到 CSV 文件中。")

if __name__ == '__main__':
    app.run(debug=True)
