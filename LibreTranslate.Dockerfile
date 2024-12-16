FROM libretranslate/libretranslate:latest

USER libretranslate

WORKDIR /app

COPY ./libretranslate_startup.sh .

EXPOSE 5000

ENTRYPOINT ["/usr/bin/env"]

CMD [ "bash", "./libretranslate_startup.sh" ]