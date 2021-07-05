. .\private.ps1

Function showmenu {
    Clear-Host
    Write-Host "------------------------------";
    Write-Host "Menu..."
    Write-Host "------------------------------";
    Write-Host "1. Buscar en Médicos Activos"
    Write-Host "2. Insertar Nuevo Médico"
    Write-Host "3. Buscar Médicos Inactivos"
    Write-Host "4. Actualizar Matricula "
    Write-Host "5. Actualizar Activo / No Activo"
    Write-Host "6. Actualizar Lugar de Trabajo"
    Write-Host "7. Exit"
}

function querydb {
    param (
        $query
    )
    $sqlcmd = New-Object System.Data.SqlClient.SqlCommand
    $sqlConn = New-Object System.Data.SqlClient.SqlConnection
    $sqlConn.ConnectionString = $connectionString
    $sqlConn.Open()
    $sqlcmd.Connection = $sqlConn
    Write-Output 'intento consulta'     
    $sqlcmd.CommandText = $query
    $adp = New-Object System.Data.SqlClient.SqlDataAdapter $sqlcmd
    $data = New-Object System.Data.DataSet
    $adp.Fill($data) | Out-Null
    $data.Tables
    $sqlConn.Close()
}
function updatedb($id,[String]$row,$value){ 
    $sqlcmd = New-Object System.Data.SqlClient.SqlCommand
    $sqlConn = New-Object System.Data.SqlClient.SqlConnection
    $sqlConn.ConnectionString = $connectionString
    $sqlConn.Open()
    $sqlcmd.Connection = $sqlConn
    #Write-Output $row
    Write-Output 'intento update'
    $query = "UPDATE Medicos SET $row = $value  where id= $id"
    #Write-Output $query
    $sqlcmd.CommandText = $query
    if ($sqlcmd.ExecuteNonQuery() -eq 1) {Write-Output "Éxito"} else {Write-Output "Falló"}
    $sqlConn.Close()
    pause
    
}


function buscarmedicoporid {
    param (
        $id, $activo
    )
    $query = "SELECT id,apellido, nombre, documento, matriculaProvincial, matriculaNacional,hospitalPrincipal,activo FROM dbo.Medicos where activo=$activo and id= $id";
    #Write-Output $query
    querydb($query)
}
function buscarmedico {
    param(
        $activo
    )
    do{
        $choice = $(Write-Host "Buscar por DNI " -NoNewLine) + $(Write-Host "[d] " -ForegroundColor yellow -NoNewLine)+$(Write-Host "o por Apellido" -NoNewLine) + $(Write-Host "[a] " -ForegroundColor yellow ; Read-Host)
        switch($choice.ToLower())
        {
            "d" {$Response = Read-Host "Escribi el DNI del médico para buscarlo en la Tabla Médicos";
                if (($Response -match '^[\d]+$') -eq $false) {break};
                $query = "SELECT id,apellido, nombre, documento, matriculaProvincial, matriculaNacional,hospitalPrincipal,activo FROM dbo.Medicos where activo="+$activo+" and documento="+$Response;          
                querydb($query)
                }
            "a" {[String]$Response = Read-Host "Escribi el Apellido del médico para buscarlo en la Tabla Médicos";         
                if (($Response -match '^[a-zA-Z]+$') -eq $false) {break};
                $query = "SELECT id,apellido, nombre, documento, matriculaProvincial, matriculaNacional,hospitalPrincipal,activo FROM dbo.Medicos where activo="+$activo+"  and apellido like  `'%"+ $Response+"%`'";
                querydb($query)
                }
            default { "Comés plastilina?" }
        }
        $Continuar = Read-Host "Buscar de nuevo? [S/N]";
    }while($Continuar.ToLower() -eq "s")   
}

function actualizarmatricula {
    do{
        do{
            $idmedico = Read-Host "Ingrese Id Médico:";
            }while (-not ($idmedico -match '^[\d]+$'))
        do{
            $matr = Read-Host "Ingrese número de matrícula";
            }while (-not ($matr -match '^[\d]+$'))
        buscarmedicoporid $idmedico 1
        $Continuar = $(Write-Host "Esta OK? [S/N] o Cancelar [C]: " -NoNewLine) + $(Write-Host "[S/N/C]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')) -and (-not ($Continuar.ToLower() -match '^c$')))
    if ($Continuar.ToLower() -eq 'c') {exit}
    $tipomatricula = $(Write-Host "Actualizar Matricula Provincial [P] o Nacional [N]: " -NoNewLine) + $(Write-Host "[P/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    switch($tipomatricula.ToLower()){
        "p"{Write-Host "Nueva Matrícula Provincial: " -NoNewLine; 
            Write-Host $matr  -ForegroundColor yellow;
            do{
                $Continuar = $(Write-Host "Proceder? [S/N]: " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
            }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')))
            if ($Continuar.ToLower() -eq 'n') {exit}
            updatedb $idmedico "matriculaProvincial" $matr
            
        }
        "n"{Write-Host "Nueva Matrícula Nacional: " -NoNewLine;
            Write-Host $matr  -ForegroundColor yellow;
            do{
                $Continuar = $(Write-Host "Proceder? [S/N]: " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
            }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')))
            if ($Continuar.ToLower() -eq 'n') {exit}
            updatedb $idmedico "matriculaNacional" $matr
            
    }
        default {"nada..";exit}
    } 
}


function actualizaractivo {
    do{
        do{
            $idmedico = Read-Host "Ingrese Id Médico:";
            }while (-not ($idmedico -match '^[\d]+$'))
        do{
            $activo = Read-Host "Ingrese activo [1] o Inactivo [0]:";
            }while (-not ($activo -match '^[1|0]$'))
        if ($activo -eq 1){buscarmedicoporid $idmedico 0}else {buscarmedicoporid $idmedico 0} 
        $Continuar = $(Write-Host "Esta OK? [S/N] o Cancelar [C]: " -NoNewLine) + $(Write-Host "[S/N/C]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')) -and (-not ($Continuar.ToLower() -match '^c$')))
    if ($Continuar.ToLower() -eq 'c') {exit}
    updatedb $idmedico "activo" $activo
    pause
}

function actualizarinterno {
    do{
        do{
            $idmedico = Read-Host "Ingrese Id Médico:";
            }while (-not ($idmedico -match '^[\d]+$'))
        do{
            $interno = Read-Host "Ingrese Interno [1] o Externo [0]:";
            }while (-not ($interno -match '^[1|0]$'))
        buscarmedicoporid $idmedico 1
        $Continuar = $(Write-Host "Esta OK? [S/N] o Cancelar [C]: " -NoNewLine) + $(Write-Host "[S/N/C]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')) -and (-not ($Continuar.ToLower() -match '^c$')))
    if ($Continuar.ToLower() -eq 'c') {exit}
    if ($interno -eq 0) {$interno=585} else {$interno=2}
    updatedb $idmedico "hospitalPrincipal" $interno
    pause
}

function insertarmedico {
    $Continuar = $(Write-Host "Desea Insertar un Médico: " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
if ($Continuar.toLower() -eq "s"){
    do{
        $sqlcmd = New-Object System.Data.SqlClient.SqlCommand
        $sqlConn = New-Object System.Data.SqlClient.SqlConnection
        $sqlConn.ConnectionString = $connectionString
        $sqlConn.Open()
        $sqlcmd.Connection = $sqlConn
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
        do{
            $interno = Read-Host "Trabaja en Hospital 1=SI 0=NO:";
        }while (-not ($interno -match '^[1|0]$'))
        do{
            $pat = Read-Host "Es Patólogo 1=SI 0=NO:";
        }while (-not ($pat -match '^[1|0]$'))

        Write-Host "Apellido: " -NoNewline 
        Write-Host  $apellido -ForegroundColor yellow
        Write-Host "Nombre: " -NoNewLine 
        Write-Host $nombre -ForegroundColor yellow
        Write-Host "DNI: " -NoNewLine 
        Write-Host $dni  -ForegroundColor yellow
        Write-Host "Trabaja en Hospital 1=SI 0=NO: " -NoNewLine 
        Write-Host $interno  -ForegroundColor yellow 
        Write-Host "Patólogo 1=SI 0=NO: " -NoNewLine 
        Write-Host $pat  -ForegroundColor yellow 
        $Continuar = $(Write-Host "Esta OK?: " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )

    }while($Continuar.ToLower() -eq "n")
    $grabar = $(Write-Host "Estás seguro que querés guardar los cambios en la tabla médicos? (No hagas cagadas te lo pido por favor): " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    if ($grabar.toLower() -eq "s"){
        if ($interno -eq 0) {$interno=585} else {$interno=2}
        Write-Output $interno
        $sqlcmd.CommandText= "INSERT INTO dbo.Medicos  (apellido, nombre, documento, hospitalPrincipal, activo,patologo) VALUES (@apellido, @nombre, @documento, @hospitalPrincipal, @activo,@patologo)"
        $sqlcmd.Parameters.Add("@apellido", [Data.SQLDBType]::VarChar, 200).Value = $apellido;
        $sqlcmd.Parameters.Add("@nombre",  [Data.SQLDBType]::VarChar, 200).Value = $nombre;
        $sqlcmd.Parameters.Add("@documento", [Data.SQLDBType]::Int).Value = $dni;
        $sqlcmd.Parameters.Add("@activo",  [Data.SQLDBType]::Int).Value = 1;
        $sqlcmd.Parameters.Add("@hospitalPrincipal", [Data.SQLDBType]::Int).Value = $interno;
        $sqlcmd.Parameters.Add("@patologo", [Data.SQLDBType]::Int).Value = $pat;
        $sqlcmd.ExecuteNonQuery();
        pause
        $sqlConn.Close();
    }
}
}



showmenu
 
while(($inp = Read-Host -Prompt "Elegir una Opción") -ne "7"){
 
switch($inp){
        1 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Buscar Médicos Activos"; 
            Write-Host "------------------------------";
            buscarmedico(1);
            break
        }
        2 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Insertar un Nuevo Médico";
            Write-Host "------------------------------";
            insertarmedico; 
            break
        }
        3 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Buscar Médicos Inactivos";
            Write-Host "------------------------------"; 
            buscarmedico(0);
            break
            }
        4 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Actualizar Matricula";
            Write-Host "------------------------------"; 
            actualizarmatricula;
            break
            }
        5 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Actualizar Activo/Inactivo";
            Write-Host "------------------------------"; 
            actualizaractivo;
            break
            }
        6 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Actualizar Interno/Externo";
            Write-Host "------------------------------"; 
            actualizarinterno;
            break
            }                
        7 {"Exit";  break}
        default {Write-Host -ForegroundColor red -BackgroundColor white "Opción Inválida";pause}
        
    }
  
showmenu
}

