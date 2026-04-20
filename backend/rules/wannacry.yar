rule WannaCry_Ransom_Note : malware family
{
    meta:
        description = "Matches common WannaCry ransom note text"
        author = "Aegis-AI"
    strings:
        $a = "Ooops, your files have been encrypted!" ascii wide
        $b = "Wana Decrypt0r" ascii wide
        $c = "@Please_Read_Me@.txt" ascii wide
    condition:
        1 of them
}

rule WannaCry_KillSwitch_Domain : malware family
{
    meta:
        description = "Matches WannaCry kill-switch domain"
        author = "Aegis-AI"
    strings:
        $domain = "iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea.com" ascii
    condition:
        $domain
}
