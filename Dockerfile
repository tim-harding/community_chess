FROM python:3.11
WORKDIR /community_chess

# Other variables from praw.ini are set by Fly.io secrets
ENV USER_AGENT="script:com.timharding.communitychess:v0.1.0 (by /u/CommunityChess_Bot)"

RUN mkdir -p src/chessbot/
ADD pyproject.toml .
ADD src/chessbot/*.py src/chessbot/
RUN pip install .
WORKDIR /
RUN rm -rf community_chess

ENTRYPOINT ["chessbot", "--log", "INFO", "--utc", "4", "--database", "/sqlite/communitychess.db", "--auth-method", "env"]
