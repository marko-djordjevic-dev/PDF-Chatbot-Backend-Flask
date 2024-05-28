from langchain.vectorstores.faiss import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_openai.chat_models import ChatOpenAI

import uuid
from flask import Blueprint, request, current_app, send_from_directory
from auth_middleware import token_required
from .. import db
from app.models.Chatbot import Chatbot
from app.models.ChatbotSession import ChatbotSession
from sqlalchemy.orm.attributes import flag_modified
from app import Config
from PyPDF2 import PdfReader
import os
import shutil

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

@chatbot_bp.route('/add_bot', methods = ['POST'])
@token_required
def add_bot(current_user):
    
    if current_user.superuser != 1:
        return {'message':'You are not allowed'}, 400

    data = request.form
    if not data['name'] or not data['prompt']:
        return {'message':'Please fill all fields'}, 400
    
    files = request.files
    file_names = []
    chatbot_id = uuid.uuid4().hex

    if not os.path.exists("upload"):
        os.mkdir("upload")

    if not os.path.exists("index_store"):
        os.mkdir("index_store")

    os.mkdir(f"upload/{chatbot_id}")

    for key, storage in files.items(multi=True):
        path = f"upload/{chatbot_id}/{storage.filename}"
        storage.save(path)

        file_names.append(storage.filename)

    detected_texts = []
    for file_name in file_names:
        detected_text = ""
        file_path = f"upload/{chatbot_id}/{file_name}"
        pdf_file_obj = open(file_path, "rb")
        pdf_reader = PdfReader(pdf_file_obj)
        num_pages = len(pdf_reader.pages)

        detected_text += f"File name: {file_name}\n"
        for page_num in range(num_pages):
            page_obj = pdf_reader.pages[page_num]
            detected_text += page_obj.extract_text() + "\n\n"

        pdf_file_obj.close()
        detected_texts.append(detected_text)

    if os.path.exists(f"upload/{chatbot_id}"):
        shutil.rmtree(f"upload/{chatbot_id}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.create_documents(detected_texts)

    vector_index = FAISS.from_documents(texts, current_app.embeddings)
    vector_index.save_local(f"index_store/{chatbot_id}")

    chatbot = Chatbot(
        name = data['name'],
        prompt = data['prompt'],
        user_id = current_user.id,
        index_name = chatbot_id,
        file_names = file_names,
        initial = 'Hi! How can I help you today?',
        suggested = 'Hello!\nWhat is chatbot?',
        placeholder = 'Write your sentences here',
    )
    db.session.add(chatbot)
    db.session.commit()

    return {
        'id': chatbot.id,
        'name': chatbot.name
    }

@chatbot_bp.route('/chatbot_list', methods = ['POST'])
@token_required
def chatbot_list(current_user):
    return  [{
            'id': chatbot.id,
            'name': chatbot.name
    } for chatbot in Chatbot.query.all()]

@chatbot_bp.route('/get_model_info', methods=['POST'])
@token_required
def get_model_info(current_user):
    bot = Chatbot.query.filter_by(id=request.json['id'], user_id = current_user.id).first()
    if bot is None:
        return {'message':'You are not allowed'}, 400
    return {
        'id':bot.id,
        'name':bot.name,
        'prompt':bot.prompt,
        'file_names':bot.file_names
    }

@chatbot_bp.route('/update_model_info', methods=['POST'])
@token_required
def update_model_info(current_user):
    bot = Chatbot.query.filter_by(id=request.json['id'], user_id = current_user.id).first()
    if bot is None:
        return {'message':'You are not allowed'}, 400
    bot.name = request.json['name']
    bot.prompt = request.json['prompt']
    db.session.commit()
    return "success"

@chatbot_bp.route('/delete_chatbot', methods=['POST'])
@token_required
def delete_chatbot(current_user):
    bot = Chatbot.query.filter_by(id=request.json['id'], user_id = current_user.id).first()
    if bot is None:
        return {'message':'You are not allowed'}, 400
    
    if os.path.exists(f"index_store/{bot.index_name}"):
        shutil.rmtree(f"index_store/{bot.index_name}")

    if os.path.exists(f"app/avatar/{bot.img_id}"):
        os.remove(f"app/avatar/{bot.img_id}")
    
    sessions = ChatbotSession.query.filter_by(chatbot_id = bot.id).all()
    for session in sessions:
        db.session.delete(session)

    db.session.delete(bot)
    db.session.commit()
    return {'message': 'Chatbot deleted successfully'}, 200

@chatbot_bp.route('/get_chatbot_setting', methods = ['POST'])
@token_required
def get_chatbot_setting(current_user):
    bot = Chatbot.query.filter_by(id=request.json['id'], user_id = current_user.id).first()
    if bot is None:
        return {'message':'You are not allowed'}, 400
    return {
        'initial' : bot.initial,
        'placeholder' : bot.placeholder,
        'suggested' : bot.suggested,
        'img_id' : bot.img_id
    }

@chatbot_bp.route('/update_chatbot_setting', methods = ['POST'])
@token_required
def update_chatbot_setting(current_user):
    bot = Chatbot.query.filter_by(id=request.form['id'], user_id = current_user.id).first()
    if bot is None:
        return {'message':'You are not allowed'}, 400
    if len(request.files) > 0:
        file_key = next(iter(request.files))
        file = request.files[file_key]
        if file:
            img_id = uuid.uuid4().hex
            file.save(f"app/avatar/{img_id}")

    bot.initial = request.form['initial']
    bot.placeholder = request.form['placeholder']
    bot.suggested = request.form['suggested']

    if len(request.files) > 0:
        bot.img_id = img_id
    db.session.commit()
    return "success"

@chatbot_bp.route('/chatbot_setting_session', methods = ['POST'])
@token_required
def chatbot_setting_session(current_user):
    session = ChatbotSession.query.filter_by(id=request.json['id']).first()
    if session is None:
        return {'message':'You are not allowed'}, 400
    bot = session.chatbot
    return {
        'initial' : bot.initial,
        'placeholder' : bot.placeholder,
        'suggested' : bot.suggested,
        'img_id' : bot.img_id
    }

@chatbot_bp.route('/create_session', methods=['POST'])
@token_required
def create_session(current_user):
    chatbot_id = request.json['chatbot_id']
    session_id = uuid.uuid4().hex

    chatbot_session = ChatbotSession(
        id= session_id,
        user_id=current_user.id,
        chatbot_id=chatbot_id,
        chat_history=[]
    )
    db.session.add(chatbot_session)
    db.session.commit()
    return session_id

@chatbot_bp.route('/get_ai_response', methods=['POST'])
@token_required
def get_ai_resposne(current_user):
    session_id = request.json['session_id']
    chatbot_session = ChatbotSession.query.filter_by(id=session_id).first()
    if chatbot_session is None:
        return {'message':'Session not found'}, 500
    
    chatbot = Chatbot.query.filter_by(id=chatbot_session.chatbot_id).first()
    if chatbot is None:
        return {'message':'Chatbot not found'}, 500
    
    vector_index = FAISS.load_local(f"index_store/{chatbot.index_name}", current_app.embeddings)
    retriever = vector_index.as_retriever(search_type="similarity", search_kwargs={"k": 6})

    llm = ChatOpenAI(temperature=0.7, api_key=Config.OPENAI_KEY, model_name='gpt-3.5-turbo')
    conv_interface = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, return_source_documents=True, verbose=False)

    db_chat_history = chatbot_session.chat_history
    if db_chat_history is None:
        db_chat_history = []
    chat_history = []
    conv_history = []

    user_string = ""
    system_string = ""
    for history in db_chat_history:
        if history.startswith("human:"):
            user_string = history[6:].strip()
        elif history.startswith("ai:"):
            system_string = history[3:].strip()
            chat_history.append({
                "human": user_string,
                "ai": system_string
            })
            conv_history.append((user_string, system_string))
            
    query = request.json['message']
    result = conv_interface({"question": query, "chat_history": conv_history})
    answer = result["answer"]

    chat_history.append({
        "human": query,
        "ai": answer
    })

    db_chat_history.append(f"human:{query}")
    db_chat_history.append(f"ai:{answer}")

    chatbot_session.chat_history = db_chat_history
    
    flag_modified(chatbot_session,'chat_history')
    db.session.commit()

    return { "answer": answer, "chat_history": chat_history }

@chatbot_bp.route('/avatar/<img_id>')
def get_image(img_id):
    return send_from_directory('avatar', img_id)