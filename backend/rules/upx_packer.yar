rule UPX_Packer_Detected : packer
{
    meta:
        description = "Detects common UPX packed executables"
        author = "Aegis-AI"
    strings:
        $upx0 = "UPX0" ascii
        $upx1 = "UPX1" ascii
        $upx2 = "UPX!" ascii
    condition:
        uint16(0) == 0x5A4D and 2 of them
}

rule UPX_Section_Names : packer
{
    meta:
        description = "Detects UPX section naming convention"
        author = "Aegis-AI"
    strings:
        $a = ".UPX0" ascii nocase
        $b = ".UPX1" ascii nocase
    condition:
        uint16(0) == 0x5A4D and all of them
}
