rule ASPack_Packer_Detected : packer
{
    meta:
        description = "Detects ASPack signatures"
        author = "Aegis-AI"
    strings:
        $aspack = "ASPack" ascii nocase
        $adata = ".aspack" ascii nocase
    condition:
        uint16(0) == 0x5A4D and any of them
}

rule Suspicious_High_Entropy_Sections : suspicious
{
    meta:
        description = "Loose packed section hint"
        author = "Aegis-AI"
    strings:
        $text = ".text" ascii
        $rsrc = ".rsrc" ascii
    condition:
        uint16(0) == 0x5A4D and #text >= 1 and #rsrc >= 1
}
