import json
import logging
import os
import threading
import time

from locust import HttpUser, task, tag, run_single_user, constant_pacing, events

sc_token = os.environ.get('SC_TOKEN')
fusion_token = os.environ.get('FUSION_TOKEN')
mh_token = os.environ.get('MH_TOKEN')


class SenseAutoApiUser(HttpUser):
    wait_time = constant_pacing(1)

    user_counter = 0
    counter_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.miaohua_task_id = None
        with SenseAutoApiUser.counter_lock:
            SenseAutoApiUser.user_counter += 1
            self.user_id = SenseAutoApiUser.user_counter

    @tag("health_check")
    @task
    def health_check_endpoint(self):
        request_start_time = time.time()
        response = self.client.get("/")

        request_end_time = time.time()
        test_result = {
            'method': 'health_check',
            'prompt': None,
            'user_id': self.user_id,
            "request_start": request_start_time,
            "request_end": request_end_time,
            "elapse_time_in_ms": int((request_end_time - request_start_time) * 1000),
            'status': response.status_code,
            'headers': response.headers,
            'body': response.json()}
        logging.info(test_result)

    @tag("sense_chat")
    @task
    def sense_chat_streaming_response(self):
        prompt = "你是谁"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': sc_token
        }
        json_payload = {
            "model": "nova-ptc-xl-v1",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": True
        }
        request_start_time = time.time()
        request_end_time = None
        finish_reason = None
        first_char_arrival_time = None

        res_delta_list = []
        with self.client.post('/sense-chat/v1/llm/chat-completions', json=json_payload, headers=headers,
                              stream=True) as streaming_response:
            status_code = streaming_response.status_code
            res_headers = streaming_response.headers
            json_response_body = None
            if streaming_response.headers.get("Content-Type").startswith("text/event-stream"):
                for data in streaming_response.iter_lines():
                    if data:
                        data_str = data.decode('utf-8')
                        sse_str = data_str[len('data: '):]

                        if str(sse_str).find("[DONE]") != -1:
                            request_end_time = time.time()
                        else:
                            sse = json.loads(data_str[len('data: '):])
                            finish_reason_str = sse.get("data", {}).get('choices', [{}])[0].get("finish_reason", "")

                            if finish_reason_str is not "" and finish_reason is None:
                                finish_reason = finish_reason_str

                            delta_str = sse.get("data", {}).get('choices', [{}])[0].get("delta", "")

                            if first_char_arrival_time is None:
                                if delta_str.strip() is not "":
                                    first_char_arrival_time = time.time()
                                else:
                                    continue
                            res_delta_list.append(delta_str)
            else:
                json_response_body = streaming_response.json()
                logging.info(json_response_body)

            test_result = {
                'method': 'sc_streaming',
                'prompt': prompt,
                'user_id': self.user_id,
                "request_start": request_start_time,
                "request_end": request_end_time,
                "elapse_time_in_ms": None if request_end_time is None else int(
                    (request_end_time - request_start_time) * 1000),
                'first_char_arrival_time': first_char_arrival_time,
                'first_char_delay_in_ms': None if first_char_arrival_time is None else int(
                    (first_char_arrival_time - request_start_time) * 1000),
                'status': status_code,
                'headers': res_headers,
                'body': json_response_body,
                'finish_reason': finish_reason,
                'res_message': ''.join(res_delta_list)}
            logging.info(test_result)

    @tag("miaohua")
    @task
    def miaohua_api(self):
        if self.miaohua_task_id is None:
            self.miaohua_task_submission()
        else:
            self.miaohua_task_result()

    def miaohua_task_result(self):
        if self.miaohua_task_id is None:
            return

        headers = {
            'Content-Type': 'application/json',
        }
        json_payload = {
            "token": mh_token,
            "task_id": self.miaohua_task_id
        }
        request_start_time = time.time()
        response = self.client.post('/miaohua/api/v1b/task_result', json=json_payload, headers=headers)
        request_end_time = time.time()
        test_result = {
            'method': 'mh_task_result',
            'prompt': None,
            'user_id': self.user_id,
            "request_start": request_start_time,
            "request_end": request_end_time,
            "elapse_time_in_ms": None if request_end_time is None else int(
                (request_end_time - request_start_time) * 1000),
            'first_char_arrival_time': None,
            'first_char_delay_in_ms': None,
            'status': response.status_code,
            'headers': response.headers,
            'body': response.json(),
            'finish_reason': None,
            'res_message': None}
        if response.status_code == 200 and len(response.json().get('info', {}).get('images', [])) != 0:
            self.miaohua_task_id = None
        logging.info(test_result)

    def miaohua_task_submission(self):
        prompt = "画个台灯"
        headers = {
            'Content-Type': 'application/json',
        }
        json_payload = {
            "token": mh_token,
            "model_name": "Artist v0.3.5 Beta",
            "prompt": prompt,
            "n_images": 1,
            "scale": 7,
            "strength": 0.6,
            "ddim_steps": 20,
            "output_size": "992x560",
            "add_prompt": False
        }
        request_start_time = time.time()
        response = self.client.post('/miaohua/api/v1b/task_submit', json=json_payload, headers=headers)
        request_end_time = time.time()
        test_result = {
            'method': 'mh_task_submit',
            'prompt': prompt,
            'user_id': self.user_id,
            "request_start": request_start_time,
            "request_end": request_end_time,
            "elapse_time_in_ms": None if request_end_time is None else int(
                (request_end_time - request_start_time) * 1000),
            'first_char_arrival_time': None,
            'first_char_delay_in_ms': None,
            'status': response.status_code,
            'headers': response.headers,
            'body': response.json(),
            'finish_reason': None,
            'res_message': None}
        if response.status_code == 200:
            task_id = response.json().get('info', {}).get('task_id', None)
            if task_id is not None:
                self.miaohua_task_id = task_id
                logging.info("Task ID" + task_id)
        logging.info(test_result)

    @tag("fusion", "fusion_mh")
    @task
    def invoke_fusion_mh_api(self):
        logging.info(f"{self.user_id}: start fusion miaohua")
        prompt = "画一张向日葵"
        self.invoke_fusion_api(prompt)
        logging.info(f"{self.user_id}: end fusion miaohua")

    @tag("fusion", "fusion_sc")
    @task
    def invoke_fusion_sc_api(self):
        logging.info(f"{self.user_id}: start fusion sensechat")
        prompt = "你是谁"
        self.invoke_fusion_api(prompt)
        logging.info(f"{self.user_id}: end fusion sensechat")

    def invoke_fusion_api(self, prompt: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': fusion_token
        }
        json_payload = {
            "max_new_tokens": 512,
            "messages": [
                {
                    "content": prompt,
                    "role": "user"
                }
            ],
            "mh_controlnet_model": "",
            "mh_key": mh_token,
            "mh_model_name": "Artist V0.3.0 Beta",
            "mh_output_size": "960x960",
            "mh_scale": 7,
            "mh_select_seed": 0,
            "mh_ddim_steps": 30,
            "mh_add_prompt": False,
            "repetition_penalty": 1,
            "output_img": True,
            "stream": True,
            "temperature": 0.8,
            "top_p": 0.7,
            "user_id": "string"
        }
        request_start_time = time.time()
        finish_reason = None
        first_char_arrival_time = None

        res_delta_list = []
        response = self.client.post('/fusion/v1/chat-with-image', json=json_payload, headers=headers,
                                    stream=True)

        if response.status_code != 200:
            logging.error(f"fusion api error: {self.user_id}: {response.status_code}, prompt: {prompt}")
            events.request.fire(
                request_type=response.request.method,
                name=response.request.path,
                response_time=response.elapsed.total_seconds() * 1000,  # Convert to milliseconds
                exception=None,
                response=response,
            )

        status_code = response.status_code
        res_headers = response.headers
        json_response_body = None
        if response.headers.get("Content-Type").startswith("text/event-stream"):
            for data in response.iter_lines():
                if data:
                    data_str = data.decode('utf-8')
                    sse_str = data_str[len('data: '):]

                    if str(sse_str).find("[DONE]") != -1:
                        logging.error("Not expecting '[DONE]' in fusion API")
                    else:
                        sse = json.loads(data_str[len('data: '):])
                        finish_reason_str = sse.get("data", {}).get('choices', [{}])[0].get("finish_reason", "")

                        if finish_reason_str is not "" and finish_reason is None:
                            finish_reason = finish_reason_str

                        delta_str = sse.get("data", {}).get('choices', [{}])[0].get("delta", "")

                        if first_char_arrival_time is None:
                            if delta_str.strip() is not "":
                                first_char_arrival_time = time.time()
                            else:
                                continue
                        res_delta_list.append(delta_str)
        else:
            json_response_body = response.json()
            logging.info(json_response_body)

        request_end_time = time.time()
        test_result = {
            'method': 'fusion',
            'prompt': prompt,
            'user_id': self.user_id,
            "request_start": request_start_time,
            "request_end": request_end_time,
            "elapse_time_in_ms": None if request_end_time is None else int(
                (request_end_time - request_start_time) * 1000),
            'first_char_arrival_time': first_char_arrival_time,
            'first_char_delay_in_ms': None if first_char_arrival_time is None else int(
                (first_char_arrival_time - request_start_time) * 1000),
            'status': status_code,
            'headers': res_headers,
            'body': json_response_body,
            'finish_reason': finish_reason,
            'res_message': ''.join(res_delta_list)}
        logging.info(test_result)

    @events.request.add_listener
    def my_request_handler(request_type, name, response_time, response_length, response,
                           context, exception, start_time, url, **kwargs):
        if exception:
            print(f"Request to {name} ({url}) failed with exception {exception}, {response.text}")

if __name__ == "__main__":
    run_single_user(SenseAutoApiUser)
