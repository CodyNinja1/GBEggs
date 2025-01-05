from GBEggs import GbxReader, GbxException

class CGameCtnChallenge:
    def __init__(self, Reader: GbxReader):
        self.Reader = Reader
        
        if Reader.ClassId != 0x3043000:
            raise GbxException("File not suitable for CGameCtnChallenge")
        else:
            self.Thumbnail = self.Reader.GetHeaderChunkById(0x3043007).Data

    @property
    def ThumbnailPillow(self):
        import io
        from PIL import Image, ImageOps
        BytesIo = io.BytesIO(self.Thumbnail)
        Version = int.from_bytes(BytesIo.read(4))

        if Version != 0:
            ThumbnailSize = int.from_bytes(BytesIo.read(4))
            BytesIo.read(len("<Thumbnail.jpg>"))
            ThumbnailData = BytesIo.read(ThumbnailSize)

        Thumbnail: Image = Image.open(io.BytesIO(ThumbnailData))
        Thumbnail = Thumbnail.rotate(180)
        BytesIo.close()
        return ImageOps.mirror(Thumbnail)
