import chess
import json
import praw
import time


#TODO make equivalent file for database loading
#returns board state and most recent url posted by bot
def from_json(jsonPath: str) -> tuple[chess.Board, str]:
    try:
        data = json.load(open(jsonPath))
    except:
        print("Failed to read from file:", jsonPath)
        return None

    latestGame = {'gameNum' : 0}
    for game in data['games']:
        if game['gameNum'] > latestGame['gameNum']:
            latestGame = game

    if (latestGame['gameNum'] == 0):
        print("JSON:", jsonPath, "incorrectly formatted or empty")
        return None

    board = chess.Board()
    latestMove = None
    try:
        for move in latestGame['moves']:
            board.push_uci(move['notation'])
            latestMove = move
    except:
        print('Illegal move list found in data base for game number:', latestGame['gameNum'])
        return None

    return (board, latestMove['moveURL'])

#Given the url to the latest move posting, find a comment that needs servicing. Return it's URL and body
def findComment(moveURL: str) -> tuple[str, str]:
    commentURL, commentBody = None
    return (commentURL, commentBody)

def createResponse(commentBody: str, board:chess.Board) -> str:
    return None

#returns true on success
def replyToReddit(response: str, commentURL: str) -> bool:
    return False

if __name__ == "__main__":
    board, moveURL = from_json('../database.json')
    if board == None:
        quit()
    print(board)
    print(moveURL)
    try:
        reddit = praw.Reddit("bot1", config_interpolation="basic")
        subreddit = reddit.subreddit('CommunityChess')
    except:
        print('Failure to connect to reddit')
        quit()

    while(True):
        commentURL, commentBody = findComment(moveURL)
        if commentURL != None:
            response = createResponse(commentBody, board)
            if not replyToReddit(response, commentURL):
                print('Failure to respond to comment')
        time.sleep(1)
