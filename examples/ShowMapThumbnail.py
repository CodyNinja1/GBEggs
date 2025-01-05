from GBEggs import GbxReader, GbxException
from Engines.Game.CGameCtnChallenge import *

Reader = GbxReader(input())
Reader.ParseAll()

try:
    Challenge = CGameCtnChallenge(Reader)
    Challenge.ThumbnailPillow.show()
except GbxException:
    print("Error: File is not CGameCtnChallenge")
