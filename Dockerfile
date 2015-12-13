FROM eliostvs/tomate

ENV PROJECT /code/

RUN apt-get update -qq && apt-get install -yq \
    dbus-x11 \
    gir1.2-gdkpixbuf-2.0 \
    gir1.2-gtk-3.0

RUN apt-get clean

COPY . $PROJECT
WORKDIR $PROJECT

ENTRYPOINT ["make"]
CMD ["test"]
