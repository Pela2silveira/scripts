. .\private.ps1
$sqlConn = New-Object System.Data.SqlClient.SqlConnection
$sqlConn.ConnectionString = $connectionString
$sqlConn.Open()
$sqlcmd = New-Object System.Data.SqlClient.SqlCommand
$sqlcmd.Connection = $sqlConn

Write-Host "Hola.."
do{
    $choice = $(Write-Host "Buscar por DNI " -NoNewLine) + $(Write-Host "[d] " -ForegroundColor yellow -NoNewLine)+$(Write-Host "o por Apellido" -NoNewLine) + $(Write-Host "[a] " -ForegroundColor yellow ; Read-Host)
    switch($choice.ToLower())
    {
        "d" {$Response = Read-Host "Escribi el DNI del médico para buscarlo en la Tabla Médicos";
            if (($Response -match '^[\d]+$') -eq $false) {exit};
            $query = "SELECT apellido, nombre, documento, matriculaProvincial, matriculaNacional FROM dbo.Medicos where activo=1 and documento="+$Response;          
            }
        "a" {[String]$Response = Read-Host "Escribi el Apellido del médico para buscarlo en la Tabla Médicos";         
            if (($Response -match '^[a-zA-Z]+$') -eq $false) {exit};
            $query = "SELECT apellido, nombre, documento, matriculaProvincial, matriculaNacional FROM dbo.Medicos where activo=1 and apellido like  `'%"+ $Response+"%`'";
            }
        default { "Comés plastilina?"; exit }
    }
#echo $query
    $sqlcmd.CommandText = $query
    $adp = New-Object System.Data.SqlClient.SqlDataAdapter $sqlcmd
    $data = New-Object System.Data.DataSet
    $adp.Fill($data) | Out-Null
    $data.Tables
    $Continuar = Read-Host "Buscar de nuevo? [S/N]";
}while($Continuar.ToLower() -eq "s")


$Continuar = $(Write-Host "Desea Insertar un Médico: " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
if ($Continuar.toLower() -eq "s"){
    do{
        do{
            $dni = Read-Host "Escribi el DNI";
        }while (-not ($dni -match '^[\d]+$'))
        do{
            $nombre = Read-Host "Escribi el Nombre";
            if ((-not ($nombre -match '.*''''.*')) -and (($nombre -match '.*''.*'))) {$nombre=$nombre.Replace('''','''''')}
        }while (-not ($nombre -match '^[a-zA-ZÀ-ÿ\u00f1\u00d1\u0027\u0020]+$')) 
        do{
            $apellido = Read-Host "Escribi el Apellido";
            if ((-not ($apellido -match '.*''''.*')) -and (($apellido -match '.*''.*'))) {$apellido=$apellido.Replace('''','''''')}
        }while (-not ($apellido -match '^[a-zA-ZÀ-ÿ\u00f1\u00d1\u0027\u0020]+$')) 
        Write-Host "Apellido: " -NoNewline 
        Write-Host  $apellido -ForegroundColor yellow
        Write-Host "Nombre: " -NoNewLine 
        Write-Host $nombre -ForegroundColor yellow
        Write-Host "DNI: " -NoNewLine 
        Write-Host $dni  -ForegroundColor yellow 
        $Continuar = $(Write-Host "Esta OK?: " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )

    }while($Continuar.ToLower() -eq "n")
    $query = "SELECT apellido, nombre, documento, matriculaProvincial, matriculaNacional FROM dbo.Medicos where activo=1 and apellido like  `'%"+ $Response+"%`'";

}
else{exit}