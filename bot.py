#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import glob
import configparser
import urllib
from urllib.request import urlopen
from urllib.parse import quote_plus
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler
from telegram import InlineQueryResultArticle, ChatAction, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from uuid import uuid4
import subprocess
import time
import logging
import json
from json import JSONDecoder
from functools import partial

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


config = configparser.ConfigParser()
config.read('bot.ini')

updater = Updater(token=config['KEYS']['bot_api'])
path = config['PATH']['path']
sudo_users = json.loads(config['ADMIN']['sudo'])
dispatcher = updater.dispatcher

def start(bot, update):
    if update.message.from_user.id in sudo_users:
        bot.sendChatAction(chat_id=update.message.chat_id,
                           action=ChatAction.TYPING)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="/actions\nSync & Build - Does a build for you and uploads here\nUpdate - runs update.sh")
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Go away")
        bot.sendChatAction(chat_id=update.message.chat_id,
                           action=ChatAction.TYPING)

def chooseBuild(bot, update):
    if update.message.from_user.id in sudo_users:
        keyboard = [[InlineKeyboardButton("Git Pull, Build and Upload", callback_data='buildClean')],

                    [InlineKeyboardButton("Build and Upload", callback_data='buildLocal')]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Please choose a build style:', reply_markup=reply_markup)

def getLog(bot, update, query):
    query = update.callback_query
    bot.sendMessage(chat_id=query.message.chat_id,
                    text="Building apps....nomnomnom",
                    parse_mode="Markdown")
    user_id = update.callback_query.from_user.id
    command = 'cd ' + path + ' && git pull && git log -5 --pretty=format:"%s"'
    print (command)
    if user_id in sudo_users:
        bot.sendChatAction(chat_id=query.message.chat_id,
                           action=ChatAction.TYPING)
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = output.stdout.read().decode('utf-8')
        output = '`{0}`'.format(output)

        bot.sendMessage(chat_id=query.message.chat_id,
                        text=output,
                        parse_mode="Markdown")

def getLogLocal(bot, update, query):
    query = update.callback_query
    user_id = update.callback_query.from_user.id
    command = 'cd ' + path + ' && git log -5 --pretty=format:"%s"'
    print (command)
    if user_id in sudo_users:
        bot.sendChatAction(chat_id=query.message.chat_id,
                           action=ChatAction.TYPING)
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = output.stdout.read().decode('utf-8')
        output = '`{0}`'.format(output)

        bot.sendMessage(chat_id=query.message.chat_id,
                        text=output,
                        parse_mode="Markdown")

def buildClean(bot, update, query):
    user_id = update.callback_query.from_user.id
    if user_id in sudo_users:
        command = "cd " + path + " && git pull && ./gradlew clean && ./gradlew assembleDebug"
        bot.editMessageText(text="Building...",
                            chat_id=query.message.chat_id,
                            message_id=query.message.message_id)
        print (command)
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
        bot.editMessageText(text="Uploading...",
                            chat_id=query.message.chat_id,
                            message_id=query.message.message_id)
        bot.sendChatAction(chat_id=query.message.chat_id,
                           action=ChatAction.TYPING)
        filename = glob.glob(path + "/app/build/outputs/apk/*")[0]
        bot.sendDocument(
                document=open(filename, 'rb'),
                chat_id=query.message.chat_id)

def buildLocal(bot, update, query):
    user_id = update.callback_query.from_user.id
    if user_id in sudo_users:
        command = "cd " + path + " && ./gradlew clean && ./gradlew assembleDebug"
        bot.editMessageText(text="Building...",
                            chat_id=query.message.chat_id,
                            message_id=query.message.message_id)
        print (command)
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()
        bot.editMessageText(text="Uploading...",
                            chat_id=query.message.chat_id,
                            message_id=query.message.message_id)
        bot.sendChatAction(chat_id=query.message.chat_id,
                           action=ChatAction.TYPING)
        filename = glob.glob(path + "/app/build/outputs/apk/*")[0]
        bot.sendDocument(
                document=open(filename, 'rb'),
                chat_id=query.message.chat_id,
                timeout=1000)

def button(bot, update, direct=True):
    user_id = update.callback_query.from_user.id
    query = update.callback_query
    if user_id in sudo_users:

        selected_button = query.data
        if selected_button == 'buildClean':
            bot.editMessageText(text="Pulling...",
                                chat_id=query.message.chat_id,
                                message_id=query.message.message_id)
            getLog(bot, update, query)
            buildClean(bot, update, query)

        if selected_button == 'buildLocal':
            bot.editMessageText(text="Skipping Git Pull...",
                                chat_id=query.message.chat_id,
                                message_id=query.message.message_id)
            getLogLocal(bot, update, query)
            buildLocal(bot, update, query)
    return False

def inlinequery(bot, update):
    query = update.inline_query.query
    o = execute(query, update, direct=False)
    results = list()

    results.append(InlineQueryResultArticle(id=uuid4(),
                                            title=query,
                                            description=o,
                                            input_message_content=InputTextMessageContent(
                                            '*{0}*\n\n{1}'.format(query, o),
                                            parse_mode="Markdown")))

    bot.answerInlineQuery(update.inline_query.id, results=results, cache_time=10)

start_handler = CommandHandler('start', start)
log_handler = CommandHandler('log', getLog)
build_handler = CommandHandler('build', chooseBuild)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(log_handler)
dispatcher.add_handler(build_handler)
dispatcher.add_handler(CallbackQueryHandler(button))
dispatcher.add_handler(InlineQueryHandler(inlinequery))
dispatcher.add_error_handler(error)

updater.start_polling()
updater.idle()
