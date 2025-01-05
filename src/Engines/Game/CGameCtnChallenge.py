from GBEggs import GbxReader, GbxException
import io

class CGameCtnChallenge:
    def __init__(self, Reader: GbxReader):
        self.Reader = Reader
        
        if Reader.ClassId != 0x3043000:
            raise GbxException("File not suitable for CGameCtnChallenge")
        else:
            ThumbnailChunk = self.Reader.GetHeaderChunkById(0x3043007)
            if ThumbnailChunk != None:
                self.Thumbnail = ThumbnailChunk.Data
            
            AuthorInfoChunk = self.Reader.GetHeaderChunkById(0x3043008)
            if AuthorInfoChunk != None:
                self.MapInfoVersion = AuthorInfoChunk.ReadUint32()
                self.AuthorVersion = AuthorInfoChunk.ReadUint32()
                self.AuthorLogin = AuthorInfoChunk.ReadString()
                self.AuthorNickname = AuthorInfoChunk.ReadString()
                self.AuthorZone = AuthorInfoChunk.ReadString()
                self.AuthorExtraInfo = AuthorInfoChunk.ReadString()
            
            XmlChunk = self.Reader.GetHeaderChunkById(0x03043005)
            if XmlChunk != None:
                self.Xml = XmlChunk.ReadString()

    def SaveChanges(self):
        ThumbnailChunk = self.Reader.GetHeaderChunkById(0x3043007)
        if ThumbnailChunk != None:
            ThumbnailChunk.SetData(self.Thumbnail)
            self.Reader.HeaderChunks[self.Reader.GetHeaderChunkIdxById(0x3043007)] = ThumbnailChunk

        AuthorInfoChunk = self.Reader.GetHeaderChunkById(0x3043008)

        if AuthorInfoChunk != None:
            AuthorInfoChunk.WriteUint32(self.MapInfoVersion)
            AuthorInfoChunk.WriteUint32(self.AuthorVersion)
            AuthorInfoChunk.WriteString(self.AuthorLogin)
            AuthorInfoChunk.WriteString(self.AuthorNickname)
            AuthorInfoChunk.WriteString(self.AuthorZone)
            AuthorInfoChunk.WriteString(self.AuthorExtraInfo)

        AuthorInfoChunk.SetDataFromWriteBuffer()
        self.Reader.HeaderChunks[self.Reader.GetHeaderChunkIdxById(0x3043008)] = AuthorInfoChunk

    @property
    def ThumbnailPillow(self):
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
