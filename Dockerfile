FROM python:3.11
WORKDIR /community_chess

RUN mkdir -p /sqlite
VOLUME /sqlite

RUN mkdir -p src/chessbot/
ADD stubs pyproject.toml praw.ini .
ADD src/chessbot/*.py src/chessbot/
RUN pip install .
CMD chessbot --log INFO --utc 4 --database /sqlite/communitychess.db
