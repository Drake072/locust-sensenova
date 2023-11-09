# Locust-Sensenova Project

## Install Dependencies
```shell
pip install -r requirements.txt
```

## Debugging your Locustfile
Reference: https://docs.locust.io/en/stable/running-in-debugger.html
![img.png](img.png)

## Start Headless Locust
Test SenseChat API Only:
```shell
SC_TOKEN='xxxxxx' MH_TOKEN='xxxx' FUSION_TOKEN='xxxx' locust --headless -H https://example.com --users 1 --only-summary --tags sense_chat
```

Test MiaoHua API Only:
```shell
SC_TOKEN='xxxxxx' MH_TOKEN='xxxx' FUSION_TOKEN='xxxx' locust --headless -H https://example.com --users 1 --only-summary --tags miao_hua
```

Test SenseChat API and Fusion-SenseChat:
```shell
SC_TOKEN='xxxxxx' MH_TOKEN='xxxx' FUSION_TOKEN='xxxx' locust --headless -H https://example.com --users 1 --only-summary --tags sense_chat fusion_sc
```