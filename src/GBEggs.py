from MiniLzo import MiniLZO

class GbxException(Exception):
    pass

class GbxChunk:
    def __init__(self, ChunkId: int, ChunkSize: int):
        self.ChunkId: int = ChunkId
        self.ChunkSize: int = ChunkSize & 0x7FFFFFFF
        self.IsHeavy: int = (ChunkSize & 0x80000000) == 2147483648
        self.Data: bytes = None
    
    def __repr__(self):
        return f"(GbxChunk ({hex(self.ChunkId)}) [{self.ChunkSize}B]{" Heavy" if self.IsHeavy else ""})\n"
    
    def SetData(self, Bytes: bytes):
        self.Data = Bytes

class GbxReader:
    def __init__(self, Filename: str):
        self.Filename: str = Filename
    
    def OpenFile(self):
        self.GbxFile = open(self.Filename, "rb")
    
    def OpenFileWrite(self, Filename: str):
        self.GbxFileWrite = open(Filename, "wb")
    
    def CloseFile(self):
        self.GbxFile.close()
    
    def CloseFileWrite(self):
        self.GbxFileWrite.close()

    def ReadBytesBE(self, Bytes: int) -> bytes:
        return self.GbxFile.read(Bytes)

    def ReadBytesLE(self, Bytes: int) -> bytes:
        return self.ReadBytesBE(Bytes)[::-1]

    def ReadUint16(self) -> int:
        return int.from_bytes(self.ReadBytesLE(2))

    def ReadUint32(self) -> int:
        return int.from_bytes(self.ReadBytesLE(4))
    
    def WriteBytesBE(self, Bytes: bytes):
        return self.GbxFileWrite.write(Bytes)

    def WriteBytesLE(self, Bytes: bytes):
        return self.WriteBytesBE(Bytes[::-1])

    def WriteUint16(self, Uint: int):
        return self.WriteBytesLE(Uint.to_bytes(2))

    def WriteUint32(self, Uint: int):
        return self.WriteBytesLE(Uint.to_bytes(4))

    def GetHeaderChunkById(self, ChunkId: int) -> GbxChunk:
        for Chunk in self.HeaderChunks:
            if Chunk.ChunkId == ChunkId:
                return Chunk
        return None

    def ParseHeaderInfo(self):
        if self.ReadBytesBE(3) != b'GBX':
            raise TypeError("File is not GBX")

        self.GbxVerison: int = self.ReadUint16()

        if self.GbxVerison >= 3:
            self.IsByteFormatBytes: bool = self.ReadBytesLE(1) == b'B'
            self.IsByteCompressionRefTableCompressed: bool = self.ReadBytesLE(1) == b'C'
            self.IsByteCompressionBodyCompressed: bool = self.ReadBytesLE(1) == b'C'
            if self.GbxVerison >= 4:
                self.ReadBytesLE(1) # HACK: skip the extra R on version 6 Gbxs

            self.ClassId: int = self.ReadUint32()

            if self.GbxVerison >= 6:
                self.UserDataSize: int = self.ReadUint32()
                self.HeaderChunkNum: int = self.ReadUint32()

                self.HeaderChunks: list[GbxChunk] = []

                for Idx in range(self.HeaderChunkNum):
                    self.HeaderChunks.append(GbxChunk(self.ReadUint32(), self.ReadUint32()))
                
                for Chunk in self.HeaderChunks:
                    Chunk.SetData(self.ReadBytesBE(Chunk.ChunkSize))

        self.NumNodes: int = self.ReadUint32()

    def ParseRefTable(self):
        self.NumExternalNodes: int = self.ReadUint32()

        if self.NumExternalNodes > 0:
            raise NotImplementedError("sowwy :3c")
    
    def ParseBody(self):
        # print(f"BODY {"UN" if not self.IsByteCompressionBodyCompressed else ""}COMPRESSED")
        self.DecompressedSize: int | None = None
        self.CompressedSize: int | None = None
        self.BodyData: bytes | None = None
        self.DecompressedBodyData: bytes | None = None

        if self.IsByteCompressionBodyCompressed:
            self.DecompressedSize = self.ReadUint32()
            self.CompressedSize = self.ReadUint32()

            self.BodyData = MiniLZO.Decompress(self.ReadBytesBE(self.CompressedSize), self.DecompressedSize)
        else:
            self.BodyData = self.ReadBytesLE(-1)
    
    def WriteHeaderInfo(self, Compress: bool = False):
        self.WriteBytesBE(b'GBX')

        self.WriteUint16(self.GbxVerison)

        if self.GbxVerison >= 3:
            self.WriteBytesBE(b'B' if self.IsByteFormatBytes else b'T')
            self.WriteBytesBE(b'C' if self.IsByteCompressionRefTableCompressed else b'U')
            self.WriteBytesBE(b'C' if Compress else b'U')

            if self.GbxVerison >= 4:
                self.WriteBytesBE(b'R') # HACK: always write R
            
            self.WriteUint32(self.ClassId)

            if self.GbxVerison >= 6:
                self.WriteUint32(self.UserDataSize)

                self.WriteUint32(self.HeaderChunkNum)

                for Chunk in self.HeaderChunks:
                    self.WriteUint32(Chunk.ChunkId)
                    self.WriteUint32(Chunk.ChunkSize)

                for Chunk in self.HeaderChunks:
                    self.WriteBytesBE(Chunk.Data)

            self.WriteUint32(self.NumNodes)

    def WriteRefTable(self):
        self.WriteUint32(self.NumExternalNodes)

        if self.NumExternalNodes > 0:
            raise NotImplementedError("sowwy :3c")

    def WriteBody(self, Compressed: bool = False):
        if Compressed:
            self.WriteUint32(self.DecompressedSize)
            self.WriteUint32(self.CompressedSize)

            self.WriteBytesBE(MiniLZO.Compress(self.BodyData))
        else:
            self.WriteBytesBE(self.BodyData)

    def ParseAll(self):
        self.OpenFile()
        self.ParseHeaderInfo()
        self.ParseRefTable()
        self.ParseBody()
        self.CloseFile()

    def SaveAll(self, Filename: str, Compress: bool = False):
        self.OpenFileWrite(Filename)
        self.WriteHeaderInfo(Compress)
        self.WriteRefTable()
        self.WriteBody(Compress)
        self.CloseFileWrite()
