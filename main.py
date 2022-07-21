import telebot
import imaplib
import re
import time
import email
from email.header import decode_header
import os

bot=telebot.TeleBot('2115088501:AAHVCZLNqOZp4Ui9Pn-5rJw3FNOiJ17671g')

class EmailNotificator:

    email='empty'
    password='empty'
    connection={}
    work_state=True
    lastMessageID=0

    def tryToConnectToIMAPServer(self,state):
        self.work_state=state
        host=self.email.split('@')[1]
        mail=imaplib.IMAP4_SSL('imap.'+host)
        connection=mail.login(self.email,self.password)
        self.connection=mail
        return connection

    def selectFolder(self,folder):
        self.connection.select(folder)

    def decodeRawEmail(self,data,id):
        last_message=data[0].split()[-1]
        if(self.lastMessageID==last_message):
            return

        self.lastMessageID=last_message
        result, data = self.connection.uid('fetch', last_message, '(RFC822)')
        message=email.message_from_bytes(data[0][1])

        body_message=[]
        attachments=[]
        bytes, encoding = decode_header(message['from'])[0]
        body_message.append('From: '+bytes.decode(encoding))
        bytes, encoding = decode_header(message['to'])[0]
        body_message.append('To: '+bytes.decode(encoding))

        try:
            bytes, encoding = decode_header(message['Subject'])[0]
            body_message.append('Subject: '+bytes.decode(encoding))
        except Exception as error:
            body_message.append('Subject: N/A')


        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8')
                    body_message.append(body)

                if part.get_content_type()=='image/jpeg':
                    filename=part.get_filename()
                    bytes, encoding = decode_header(filename)[0]
                    filename=bytes.decode(encoding)
                    with open(filename,'wb') as new_file:
                        new_file.write(part.get_payload(decode=True))
                        attachments.append(filename)
        else:
            body=message.get_payload(decode=True).decode('utf-8')
            body_message.append(body)
        new_message='\n'.join(body_message)
        self.sendNewMessage(new_message,id,attachments)

    def sendNewMessage(self,new_message,id,attachments=[]):
        bot.send_message(id,new_message)
        for attachment in attachments:
            bot.send_photo(id,photo=open(attachment, 'rb'))
            os.remove(attachment)

    def interruptWorking(self,message):
        if(message.text=='stop'):
            self.work_state=False

    def getNewMessages(self,user_message):
        while True:
            if(self.work_state==False):
                break
            self.selectFolder('inbox')
            result,data=self.connection.uid('search', None, 'ALL')
            self.decodeRawEmail(data,user_message.chat.id)
            bot.register_next_step_handler(user_message, self.interruptWorking)
            time.sleep(3)



Notificator=EmailNotificator()


@bot.message_handler(commands=['start'])
def greet_client(message):
    bot.send_message(message.chat.id,'Привет, я бот-менеджер электронной почты. Благодаря мне, ты сможешь получать уведомления о новых письмах прямо в телеграмме! Для начала работы введи свою почту:')
    bot.register_next_step_handler(message,get_users_email)


def start_work_again_after_disabling(message):
    bot.send_message(message.chat.id,'Желаете начать новую рассылку? Введите почту:')
    bot.register_next_step_handler(message,get_users_email)

def get_users_email(message):
    if re.match('[^@]+@[^@]+\.[^@]+',message.text):
        bot.send_message(message.chat.id,'Отлично, теперь введи пароль от своей почты. Все данные засекречены')
        bot.register_next_step_handler(message,get_users_password)
        Notificator.email=message.text
        return
    bot.send_message(message.chat.id,'Невалидная почта')
    bot.register_next_step_handler(message,get_users_email)

def get_users_password(message):
    Notificator.password=message.text
    try:
        Notificator.tryToConnectToIMAPServer(True)
    except Exception as error:
        bot.send_message(message.chat.id,'Неверная почта или пароль.Попробуйте ввести данные заново. Почта:')
        bot.register_next_step_handler(message,get_users_email)
    else:
        bot.send_message(message.chat.id, 'Рассылка email начата. Чтобы остановить рассылку, напишите "stop"')
        Notificator.getNewMessages(message)
        bot.send_message(message.chat.id, 'Рассылка email отсановлена.')
        Notificator.connection.close()
        start_work_again_after_disabling(message)

bot.polling(none_stop=True)