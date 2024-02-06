FROM python:3.11.6
COPY requirements.txt /userapp/requirements.txt
WORKDIR /userapp
RUN pip install -r requirements.txt
COPY app.py /userapp/
ENTRYPOINT ["python"]
CMD ["app.py"]