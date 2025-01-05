from MiniLzo import MiniLZO
from io import BytesIO

class GbxException(Exception):
    pass

class GbxNod:
    def __init__(self, Data: bytes):
        self.Data = Data
    
    def __repr__(self):
        return f"(GbxNod [{self.Data[:10]}])\n"

class GbxChunk:
    def __init__(self, ChunkId: int, ChunkSize: int):
        self.ChunkId: int = ChunkId
        self.ChunkSize: int = ChunkSize & 0x7FFFFFFF
        self.IsHeavy: int = (ChunkSize & 0x80000000) == 2147483648
        self.Data: bytes = None
        self.DataIo: BytesIO = None
        self.DataIoWrite: BytesIO = BytesIO()
    
    def __repr__(self):
        return f"(GbxChunk ({hex(self.ChunkId)}) [{self.ChunkSize}B]{" Heavy" if self.IsHeavy else ""})\n"
    
    def ReadBytesBE(self, Bytes: int) -> bytes:
        return self.DataIo.read(Bytes)
    
    def ReadBytesWriteBE(self, Bytes: int) -> bytes:
        return self.DataIoWrite.read(Bytes)

    def ReadBytesLE(self, Bytes: int) -> bytes:
        return self.ReadBytesBE(Bytes)[::-1]

    def ReadUint16(self) -> int:
        return int.from_bytes(self.ReadBytesLE(2))

    def ReadUint32(self) -> int:
        return int.from_bytes(self.ReadBytesLE(4))

    def ReadString(self) -> str:
        Length = self.ReadUint32()
        return self.ReadBytesBE(Length).decode("utf-8")
    
    def WriteBytesBE(self, Bytes: int):
        self.DataIoWrite.write(Bytes)

    def WriteBytesLE(self, Bytes: int):
        self.WriteBytesBE(Bytes[::-1])

    def WriteUint16(self, Uint: int):
        self.WriteBytesLE(Uint.to_bytes(2))

    def WriteUint32(self, Uint: int) -> int:
        self.WriteBytesLE(Uint.to_bytes(4))

    def WriteString(self, Str: str) -> str:
        EncodedStr = Str.encode("utf-8")
        self.WriteUint32(len(EncodedStr))
        self.WriteBytesBE(EncodedStr)
    
    def SetDataFromWriteBuffer(self):
        self.DataIoWrite.seek(0)
        self.Data = self.ReadBytesWriteBE(-1)
        self.ChunkSize = len(self.Data)

    def SetData(self, Bytes: bytes):
        self.Data = Bytes
        self.DataIo = BytesIO(self.Data)

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
        self.GbxFileWrite.write(Bytes)

    def WriteBytesLE(self, Bytes: bytes):
        self.WriteBytesBE(Bytes[::-1])

    def WriteUint16(self, Uint: int):
        self.WriteBytesLE(Uint.to_bytes(2))

    def WriteUint32(self, Uint: int):
        self.WriteBytesLE(Uint.to_bytes(4))

    def GetHeaderChunkById(self, ChunkId: int) -> GbxChunk:
        for Chunk in self.HeaderChunks:
            if Chunk.ChunkId == ChunkId:
                return Chunk
        return None

    def GetHeaderChunkIdxById(self, ChunkId: int) -> GbxChunk:
        for Idx, Chunk in enumerate(self.HeaderChunks):
            if Chunk.ChunkId == ChunkId:
                return Idx
        return -1

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
        self.DecompressedSize: int | None = None
        self.CompressedSize: int | None = None
        self.BodyData: bytes | None = b''
        self.DecompressedBodyData: bytes | None = None
        self.Chunks: list[GbxChunk] = []

        if self.IsByteCompressionBodyCompressed:
            self.DecompressedSize = self.ReadUint32()
            self.CompressedSize = self.ReadUint32()

            self.BodyData = MiniLZO.Decompress(self.ReadBytesBE(self.CompressedSize), self.DecompressedSize)
        else:
            self.BodyData = self.ReadBytesLE(-1)
        
        self.BodyDataIo = BytesIO(self.BodyData)

        # Parse Chunks from Body
        while self.BodyDataIo.tell() < len(self.BodyData) - 1:
            ChunkId = int.from_bytes(self.BodyDataIo.read(4))
            ChunkSize = int.from_bytes(self.BodyDataIo.read(4))

            self.Chunks.append(GbxChunk(ChunkId, ChunkSize))
            self.Chunks[-1].SetData(self.ReadBytesBE(ChunkSize))
            print(self.BodyDataIo.tell())
    
    def GetSumSizeOfUserData(self):
        Size = 4
        for Chunk in self.HeaderChunks:
            Size += Chunk.ChunkSize + 8
        return Size

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
                self.UserDataSize = self.GetSumSizeOfUserData()
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

    def ToFile(self, Filename: str, Compress: bool = False):
        self.OpenFileWrite(Filename)
        self.WriteHeaderInfo(Compress)
        self.WriteRefTable()
        self.WriteBody(Compress)
        self.CloseFileWrite()
