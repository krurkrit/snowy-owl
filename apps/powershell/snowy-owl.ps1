# Snowy Owl PSReadLine personalization
# This file is generated. The installer inserts this content as a marked block in $PROFILE.
if (Get-Module -ListAvailable -Name PSReadLine) {
    Set-PSReadLineOption -Colors @{
        Command   = '\e[38;2;20;80;160m'
        Keyword   = '\e[38;2;138;63;0m'
        String    = '\e[38;2;18;99;61m'
        Number    = '\e[38;2;138;63;0m'
        Variable  = '\e[38;2;20;80;160m'
        Parameter = '\e[38;2;20;80;160m'
        Operator  = '\e[38;2;24;25;27m'
        Comment   = '\e[38;2;92;97;102m'
        Error     = '\e[38;2;165;40;52m'
    }
}
