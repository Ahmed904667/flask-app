import os
import uuid
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import boto3

app = Flask(__name__)

# AWS setup
AWS_REGION = 'us-east-1'
S3_BUCKET = 'my-flask-app-images'  # ← change this to your actual bucket name

s3 = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table('MessagesTable')

@app.route('/')
def index():
    response = table.scan()
    posts = response.get('Items', [])
    return render_template('index.html', posts=posts, bucket=S3_BUCKET)

@app.route('/upload', methods=['POST'])
def upload():
    message = request.form['message']
    image = request.files['image']
    filename = secure_filename(image.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    
    # Upload to S3
    s3.upload_fileobj(image, S3_BUCKET, unique_filename, ExtraArgs={'ACL': 'public-read'})

    # Save metadata in DynamoDB
    post_id = str(uuid.uuid4())
    table.put_item(Item={
        'id': post_id,
        'message': message,
        'image': unique_filename
    })

    return redirect(url_for('index'))

@app.route('/edit/<post_id>', methods=['GET', 'POST'])
def edit(post_id):
    if request.method == 'POST':
        message = request.form['message']
        table.update_item(
            Key={'id': post_id},
            UpdateExpression='SET message = :val1',
            ExpressionAttributeValues={':val1': message}
        )
        return redirect(url_for('index'))

    response = table.get_item(Key={'id': post_id})
    post = response.get('Item')
    return render_template('edit.html', post=post)

@app.route('/delete/<post_id>')
def delete(post_id):
    # Delete image from S3
    response = table.get_item(Key={'id': post_id})
    post = response.get('Item')
    if post:
        s3.delete_object(Bucket=S3_BUCKET, Key=post['image'])
    table.delete_item(Key={'id': post_id})
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
