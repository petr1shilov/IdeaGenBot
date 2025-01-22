import re
from datetime import datetime
import requests
import uuid
import json
import config
import time
from openai import OpenAI
import logging

api_logger = logging.getLogger('api_logger')

# Настраиваем формат и уровень логирования только для нашего логгера
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(name)s - %(message)s')
handler.setFormatter(formatter)
api_logger.addHandler(handler)
api_logger.setLevel(logging.INFO)

class IdeaGenAPI:

    def __init__(self, auth_gpt=config.auth_gpt):
        self.auth_gpt = auth_gpt
        self.client = OpenAI(api_key=config.auth_gpt)
        


    def parsing_agents(self, text_agent):
        request_text = re.split(r"\[.+\]", text_agent)
        request_text = request_text[1:]
        clean_request_text = [re.sub(r"[\n]", "", i) for i in request_text]
        request_name = re.findall(r"\[.+\]", text_agent)

        agents = {}
        for i in range(len(request_name)):
            agents[request_name[i]] = clean_request_text[i]
        return agents
    
    def get_gpt4_completion(self, conversation_history):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history
            )
        return response
    
    def get_answer(self, agents, theme, history, first_messege, len_dialog: int = 1):

        content = []
        count = 1
        total_tokens = 0
        # first_messege = True
        total_prompt_tokens = 0
        total_completion_tokens = 0

        agents = self.parsing_agents(agents)

        system_prompt = f'Представь что это брейншторм {len(agents)} людей на тему: {theme}.\n\n'
        for agent in agents:
            text = f'''Специалист номер {count} - Тебя зовут {agent}. Ты {agents[agent]} 
            Ты участвуешь в научном брейншторме на тему {theme} вместе с:
            {set(agents) - set([agent])}. 
            Все специалисты говорят по очереди.\n\n'''
    
            system_prompt += text
            count += 1
        if len(history) < 2:
            conversation_history = [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ] + history 
        else: 
            conversation_history = history + [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ]
        for _ in range(len_dialog):
            for agent in agents:
                if first_messege:
                    prompt = f"""
                    Cейчас очередь {agent}.
                    Ты говоришь первым, поэтому не забудь поздароваться.
                    Начни диалог по теме.
                    Твой ответ должен быть 1-2 предложения. В каждом предожении примерно 7 слов. Скажи только саму реплику.
                    """
                    # first_messege = False
                else:
                    prompt = f"""
                    Cейчас очередь {agent}.
                    Дополни, покритикуй или предложи альтернативу обсуждаемым идеям на ответы предыдущего специалиста.
                    Твой ответ должен быть 1-2 предложения. В каждом предожении примерно 7 слов. Скажи только саму реплику, не начинай с имени {agent} и не надо здороватся.
                    """
                conversation_history.append({"role": "user", "content": prompt})

                answer = self.get_gpt4_completion(conversation_history)

                conversation_history.append(
                    {
                        "role": "assistant",
                        "content": answer.choices[0].message.content,
                    }
                )
                content.append({agent: answer.choices[0].message.content})
                total_prompt_tokens += int(answer.usage.prompt_tokens)
                total_completion_tokens += int(answer.usage.completion_tokens)
            
        print(content, conversation_history)
        return content, conversation_history
                
    def get_result(self, agents, theme, history):
        takeoffs_system_prompt = f"""Ты опытный ученый, который подводит итог научного диспута на тему:{theme}. 
                    В диалоге участвуют: {agents}. 
                    Текст диалога: 
                        начало диалога: {history} 
                        конец диалога. 
                    Сформируй нумерованный список ценных идей, озвученых в диалоге, приведи не менее 1 идеи.
                    Не надо упоминать участников диалога в своем ответе"""
        conversation_history_takeoffs = [
            {"role": "system", "content": takeoffs_system_prompt}
        ]
        answer_total = self.get_gpt4_completion(conversation_history_takeoffs)

        # total_prompt_tokens += int(answer_total.usage.prompt_tokens)
        # total_completion_tokens += int(answer_total.usage.completion_tokens)

        # print((f'всего было потрачено --> {total_prompt_tokens + total_completion_tokens} токенов\n'
        #        f'на вход было потрачено --> {total_prompt_tokens}токенов\n' 
        #        f'на ответ было потрачено --> {total_completion_tokens}токенов\n' 
        #        f' на {len(agents) + 1} реплик'))

        return answer_total.choices[0].message.content
    