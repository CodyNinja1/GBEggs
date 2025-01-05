from GBEggs import GbxReader
from Engines.Game.CGameCtnChallenge import *

Reader = GbxReader(input())
Reader.ParseAll()

Challenge = CGameCtnChallenge(Reader)

Challenge.ThumbnailPillow.show()
