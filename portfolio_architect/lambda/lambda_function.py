import os
import json
import yfinance as yf
import boto3
from datetime import datetime, timedelta


s3 = boto3.client('s3')


def get_named_parameter(event, name):
    # Get the value of a specific parameter from the Lambda event
    for param in event['parameters']:
        if param['name'] == name:
            return param['value']
    return None


def get_available_products():
    bucket_name = os.environ['S3_BUCKET_NAME']
    file_name = 'available_products.json'
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=file_name)
        content = response['Body'].read().decode('utf-8')
        products = json.loads(content)
        return products
    
    except Exception as e:
        print(f"Error reading from S3: {e}")
        return {"error": str(e)}


def get_product_data(ticker):
    try:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=100)

        product_data = {}
        etf = yf.Ticker(ticker)
        hist = etf.history(start=start_date, end=end_date)

        # Store closing prices for each asset
        product_data[ticker] = {
            date.strftime('%Y-%m-%d'): round(price, 2) for date, price in hist['Close'].items()
        }

        return product_data

    except Exception as e:
        print(f"Error fetching asset prices: {e}")
        return {"error": str(e)}


def lambda_handler(event, context):
    print(context.client_context)
    print(event)
    tool_name = context.client_context.custom['bedrockAgentCoreToolName']
    
    # delimeter
    function_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name

    if 'get_available_products' == function_name:
        output = get_available_products()
    elif 'get_product_data' == function_name:
        ticker = event.get('ticker', "")
        output = get_product_data(ticker)
    else:
        output = 'Invalid function'

    return {'statusCode': 200, 'body': json.dumps(output, ensure_ascii=False)}
