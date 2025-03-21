import re
import time
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import openai

app = Flask(__name__)

# 🔑 Configuração das Chaves de API
openai.api_key = "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"
assistant_id = "asst_tYHKuTc8tAUGK6T1cMhyi7Rb"

def clean_text(response_text):
    """Remove elementos indesejados da resposta, sem afetar a precisão."""
    if not response_text:
        return ""

    # Remover referências no formato 【n:n†source】 ou similares
    response_text = re.sub(r"【\d+:\d+†source】", "", response_text)

    # Remover referências como [n] ou (n)
    response_text = re.sub(r"\[\d+\]", "", response_text)  # Remove [1], [2], etc.
    response_text = re.sub(r"\(\d+\)", "", response_text)  # Remove (1), (2), etc.

    # Remover linhas que mencionam "Fonte", "Referência", "Documentos utilizados", etc.
    response_text = re.sub(r"(?i)(Fonte:|Referência:|Essas informações foram obtidas nos seguintes documentos:).*", "", response_text)

    # Remover espaços extras e normalizar a formatação
    response_text = response_text.strip()
    
    return response_text

def get_or_create_thread(user_id):
    """Cria ou recupera um thread de conversa para manter o contexto das respostas."""
    try:
        thread = openai.beta.threads.create()
        return thread.id
    except Exception as e:
        print(f"❌ ERRO ao criar thread: {e}")
        return None

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Recebe mensagens do WhatsApp e responde de forma otimizada."""
    try:
        incoming_msg = request.form.get("Body")  # Mensagem do usuário
        sender = request.form.get("From")  # Número do remetente

        if not incoming_msg:
            return "Erro: Mensagem vazia recebida.", 400

        thread_id = get_or_create_thread(sender)

        if not thread_id:
            return "Erro ao criar thread no OpenAI.", 500

        # Envia a mensagem para o Assistente OpenAI
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=incoming_msg
        )

        # Inicia o processamento da resposta do Assistente
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # Aguarda a resposta estar pronta
        while run.status in ["queued", "in_progress"]:
            time.sleep(2)
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        # Obtém a resposta do Assistente
        messages = openai.beta.threads.messages.list(thread_id=thread_id)

        if not messages.data:
            return "Erro: O assistente não retornou uma resposta.", 500

        reply_text = messages.data[0].content[0].text.value

        # 🔥 Limpa a resposta de elementos indesejados
        cleaned_reply = clean_text(reply_text)

        # Envia a resposta via Twilio
        twilio_resp = MessagingResponse()
        twilio_resp.message(cleaned_reply)

        return str(twilio_resp)

    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        return "Erro interno no servidor.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True)
