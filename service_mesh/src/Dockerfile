FROM node:10

WORKDIR /usr/src/nodeapp

COPY . .

# build npm dependencies
RUN npm install

EXPOSE 8080

CMD ["node", "index.js"]