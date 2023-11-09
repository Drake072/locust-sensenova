import json
import logging
import os
import threading
import time

from locust import HttpUser, between, task, tag, run_single_user

auth_token = os.environ.get('LOAD_TEST_TOKEN')


class SenseAutoApiUser(HttpUser):
    wait_time = between(0.0, 0.5)

    user_counter = 0
    counter_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        question = "你是谁"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_token
        }
        json_payload = {
            "model": "nova-ptc-xl-v1",
            "messages": [
                {
                    "role": "user",
                    "content": question
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


if __name__ == "__main__":
    run_single_user(SenseAutoApiUser)
