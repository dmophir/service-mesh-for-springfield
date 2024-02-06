FROM python:3.11.6
COPY requirements.txt /productapp/requirements.txt
WORKDIR /productapp
RUN pip install -r requirements.txt
COPY . /productapp
COPY data/ /productapp/data/
COPY data/catalog.yml /productapp/data/catalog.yml
ENTRYPOINT ["python"]
CMD ["run.py"]