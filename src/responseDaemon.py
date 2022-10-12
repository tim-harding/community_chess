from http.client import FORBIDDEN
import json
import praw
import time
import game
import comment

class Daemon:
    def __init__(self, jsonPath: str):
        postSubmissionID, self.game = self.from_json(jsonPath)
        try:
            self.reddit = praw.Reddit("bot1", config_interpolation="basic")
            self.currentSubmission = self.reddit.submission(postSubmissionID) #The post that is being monitored
        except:
            print('Failure to connect to reddit')
            quit()


    #TODO make equivalent file for database loading
    #returns game object and post ID of most recent post by bot
    def from_json(self, jsonPath: str) -> tuple[str, game.Game]:
        try:
            data = json.load(open(jsonPath))
        except:
            print("Failed to read from file:", jsonPath)
            return None

        latestMatch = {'gameNum' : 0}
        for match in data['games']:
            if match['gameNum'] > latestMatch['gameNum']:
                latestMatch = match

        if (latestMatch['gameNum'] == 0):
            print("JSON:", jsonPath, "incorrectly formatted or empty")
            return None

        latestMove = None
        moves = []
        try:
            for move in latestMatch['moves']:
                moves.append(move['notation'])
                latestMove = move
        except:
            print('Illegal move list found in data base for game number:', latestMatch['gameNum'])
            return None

        return (latestMove['postSubmissionID'], game.Game(moves))

    #Given the daemon's currentSubmission, find a comment that needs servicing. Return it's object
    def findComment(self) -> comment.Comment:
        commentBody, commentUpvotes, commentID = None, None, None
        self.currentSubmission.comments.replace_more(limit=0)
        for top_level_comment in self.currentSubmission.comments:
            beenServiced = False
            for second_level_comment in top_level_comment.replies:
                if second_level_comment.author == self.reddit.user.me():
                    beenServiced = True
                    break
            if (not beenServiced):
                commentBody, commentUpvotes, commentID = top_level_comment.body, top_level_comment.score, top_level_comment.id
                break

        return comment.Comment(commentBody, commentUpvotes, commentID)



if __name__ == "__main__":
    daemon = Daemon('../database.json')
    print(daemon.game.board)
    print(daemon.currentSubmission)

    while(True):
        Acomment = daemon.findComment()
        if Acomment.ID != None:
            response = Acomment.formulateResponse(daemon.game.board)
            print(response)
            try:
                daemon.reddit.comment(Acomment.ID).reply(body = response)
            except:
                print('Failure to respond to comment with ID:', Acomment.ID)
        time.sleep(10)
