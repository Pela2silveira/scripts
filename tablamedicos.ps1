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
    Write-Host "7. Actualizar Tabla Medicos_Funciones"
    Write-Host "8. Exit"
}
function insertdb{
    param ($query )
    $sqlcmd = New-Object System.Data.SqlClient.SqlCommand
    $sqlConn = New-Object System.Data.SqlClient.SqlConnection
    $sqlConn.ConnectionString = $connectionString
    $sqlConn.Open()
    $sqlcmd.Connection = $sqlConn
    $sqlcmd.CommandText= $query
    Write-Output 'intento insert'     
    $sqlcmd.ExecuteNonQuery();
    $sqlConn.Close();
    pause
}
function querydb {
    param ( $query )
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
    $sqlConn.Close()
    return $data  
}
function updatedb($id,$row,$value){ 
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
    param ( $id, $activo )
    $query = "SELECT id,apellido, nombre, documento, matriculaProvincial, matriculaNacional,hospitalPrincipal,activo FROM dbo.Medicos where activo=$activo and id= $id"
    #Write-Output $query
    $data = New-Object System.Data.DataSet
    $data=querydb $query
    return $data
}
function buscarmedico{
    param(
        $activo
    )
    do{
        $choice = $(Write-Host "Buscar por DNI " -NoNewLine) + $(Write-Host "[d] " -ForegroundColor yellow -NoNewLine)+$(Write-Host "o por Apellido" -NoNewLine) + $(Write-Host "[a] " -ForegroundColor yellow ; Read-Host)
        switch($choice.ToLower())
        {
            "d" {$Response = Read-Host "Escribi el DNI del médico para buscarlo en la Tabla Médicos"
                if (($Response -match '^[\d]+$') -eq $false) {break};
                $query = "SELECT id,apellido, nombre, documento, matriculaProvincial, matriculaNacional,hospitalPrincipal,activo FROM dbo.Medicos where activo=$activo and documento=$Response"        
                $data = New-Object System.Data.DataSet
                $data=querydb $query 
                foreach ($Row in $data.tables[0].Rows){Write-Output $Row }
                Write-Output "cantidad de resultados" $data.tables[0].Rows.count
                break}
            "a" {$Response = Read-Host "Escribi el Apellido del médico para buscarlo en la Tabla Médicos"      
                if (($Response -match '^[a-zA-Z]+$') -eq $false) {break}
                $query = "SELECT id,apellido, nombre, documento, matriculaProvincial, matriculaNacional,hospitalPrincipal,activo FROM dbo.Medicos where activo="+$activo+"  and apellido like  `'%"+ $Response+"%`'";
                $data = New-Object System.Data.DataSet
                $data=querydb $query
                foreach ($Row in $data.tables[0].Rows){
                    Write-Output $Row
                }
                Write-Output "cantidad de resultados" $data.tables[0].Rows.count
                break
                }
            default { "Comés plastilina?" }
        }
        $Continuar = Read-Host "Buscar de nuevo? [S/N]";
    }while($Continuar.ToLower() -eq "s")   
}

function actualizarmatricula {
    do{
        do{
            $idmedico = Read-Host "Ingrese Id Médico";
            }while (-not ($idmedico -match '^[\d]+$'))
        do{
            $matr = Read-Host "Ingrese número de matrícula";
            }while (-not ($matr -match '^[\d]+$'))
        $data = New-Object System.Data.DataSet
        $data=buscarmedicoporid $idmedico 1
        foreach ($Row in $data.tables[0].Rows){
            Write-Output $Row
        }
        if ($data.tables[0].Rows.count -eq 0) {exit}
        $Continuar = $(Write-Host "Esta OK? [S/N] o Cancelar [C] " -NoNewLine) + $(Write-Host "[S/N/C]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')) -and (-not ($Continuar.ToLower() -match '^c$')))
    if ($Continuar.ToLower() -eq 'c') {exit}
    $tipomatricula = $(Write-Host "Actualizar Matricula Provincial [P] o Nacional [N] " -NoNewLine) + $(Write-Host "[P/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    switch($tipomatricula.ToLower()){
        "p"{Write-Host "Nueva Matrícula Provincial " -NoNewLine; 
            Write-Host $matr  -ForegroundColor yellow;
            do{
                $Continuar = $(Write-Host "Proceder? [S/N] " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
            }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')))
            if ($Continuar.ToLower() -eq 'n') {exit}
            updatedb $idmedico "matriculaProvincial" $matr
            break
        }
        "n"{Write-Host "Nueva Matrícula Nacional " -NoNewLine;
            Write-Host $matr  -ForegroundColor yellow;
            do{
                $Continuar = $(Write-Host "Proceder? [S/N] " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
            }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')))
            if ($Continuar.ToLower() -eq 'n') {exit}
            updatedb $idmedico "matriculaNacional" $matr
            break
    }
        default {"nada..";break}
    } 
}


function actualizaractivo {
    do{
        do{
            $idmedico = Read-Host "Ingrese Id Médico";
            }while (-not ($idmedico -match '^[\d]+$'))
        do{
            $activo = Read-Host "Ingrese activo [1] o Inactivo [0]";
            }while (-not ($activo -match '^[1|0]$'))
        $data = New-Object System.Data.DataSet
    
        if ($activo -eq 1){$data=buscarmedicoporid $idmedico 0}else {$data=buscarmedicoporid $idmedico 1}
        foreach ($Row in $data.tables[0].Rows){
            Write-Output $Row
        }
        if ($data.tables[0].Rows.count -eq 0) {exit} 
        $Continuar = $(Write-Host "Esta OK? [S/N] o Cancelar [C] " -NoNewLine) + $(Write-Host "[S/N/C]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')) -and (-not ($Continuar.ToLower() -match '^c$')))
    if ($Continuar.ToLower() -eq 'c') {exit}
    updatedb $idmedico "activo" $activo
}

function actualizarinterno {
    do{
        do{
            $idmedico = Read-Host "Ingrese Id Médico";
            }while (-not ($idmedico -match '^[\d]+$'))
        do{
            $interno = Read-Host "Ingrese Interno [1] o Externo [0]";
            }while (-not ($interno -match '^[1|0]$'))
        $data= New-Object System.Data.DataSet
        $data = buscarmedicoporid $idmedico 1
        if ($data.tables[0].Rows.count -eq 0) {exit}
        $Continuar = $(Write-Host "Esta OK? [S/N] o Cancelar [C] " -NoNewLine) + $(Write-Host "[S/N/C]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not ($Continuar.ToLower() -match '^s$')) -and (-not ($Continuar.ToLower() -match '^n$')) -and (-not ($Continuar.ToLower() -match '^c$')))
    if ($Continuar.ToLower() -eq 'c') {exit}
    if ($interno -eq 0) {$interno=585} else {$interno=2}
    updatedb $idmedico "hospitalPrincipal" $interno
    pause
}

function insertarmedico {
    
    do{
        $dni = Read-Host "Escribi el DNI";
    }while (-not ($dni -match '^[\d]+$'))
    do{
        $pat = Read-Host "Es Patólogo 1=SI 0=NO";
    }while (-not ($pat -match '^[1|0]$'))
    do{
        $Continuar = $(Write-Host "Desea Insertar un Médico Externo " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    }while ((-not($Continuar.toLower() -eq "s")) -and (-not($Continuar.toLower() -eq "n")))
    if ($Continuar.toLower() -eq "s"){
        $interno=0
        $numeroagente=$dni
        do{
            $nombre = Read-Host "Escribi el Nombre";
            if ((-not ($nombre -match '.*''''.*')) -and (($nombre -match '.*''.*'))) {$nombre=$nombre.Replace('''','''''')}
        }while (-not ($nombre -match '^[a-zA-ZÀ-ÿ\u00f1\u00d1\u0027\u0020]+$')) 
        do{
            $apellido = Read-Host "Escribi el Apellido";
            if ((-not ($apellido -match '.*''''.*')) -and (($apellido -match '.*''.*'))) {$apellido=$apellido.Replace('''','''''')}
        }while (-not ($apellido -match '^[a-zA-ZÀ-ÿ\u00f1\u00d1\u0027\u0020]+$')) 
    }
    else{
        $interno=1
        $data = New-Object System.Data.DataSet
        $query = "select id, numero, documento, Apellido, nombre from Personal_Agentes where documento= '$dni'"
        #Write-Output $query
        $data=querydb $query
        foreach ($Row in $data.tables[0].Rows){
            Write-Output $Row
        }
        Write-Output "Cantidad de resultados en Tabla Personal Agentes" $data.tables[0].Rows.count
        switch ($data.tables[0].Rows.count) {
            0 {
                Write-Output "No existe ningún agente cargado con el DNI Ingresado. Si es agente es de reciente ingreso puede no haber sido dado de alta aún, en cuyo caso puede cargarse con el DNI. Caso contrario reportar el problema a Plataforma"
                do{
                    $Continuar = $(Write-Host "¿Desea cargar con Numero de Agente igual al DNI?" -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
                } while ((not($Continuar.ToLower() -eq "s")) -and (not($Continuar.ToLower() -eq "n"))) 
                if ($Continuar.ToLower -eq 's') {
                    $numeroagente=$dni
                    do{
                        $nombre = Read-Host "Escribi el Nombre";
                        if ((-not ($nombre -match '.*''''.*')) -and (($nombre -match '.*''.*'))) {$nombre=$nombre.Replace('''','''''')}
                    }while (-not ($nombre -match '^[a-zA-ZÀ-ÿ\u00f1\u00d1\u0027\u0020]+$')) 
                    do{
                        $apellido = Read-Host "Escribi el Apellido";
                        if ((-not ($apellido -match '.*''''.*')) -and (($apellido -match '.*''.*'))) {$apellido=$apellido.Replace('''','''''')}
                    }while (-not ($apellido -match '^[a-zA-ZÀ-ÿ\u00f1\u00d1\u0027\u0020]+$')) 
                } else {return}
                break
            }
            1 {
                #$numeroagente=
                $numeroagente= $data.tables[0].Rows[0]["numero"]  
                $apellido= $data.tables[0].Rows[0]["Apellido"]
                $nombre = $data.tables[0].Rows[0]["nombre"]
                break
            }
            Default {
                Write-Output "Existe más de un agente con ese dni en la base de datos. Reportar el problema a Plataforma"
                return
            }
        }
        }
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
    $grabar = $(Write-Host "Estás seguro que querés guardar los cambios en la tabla médicos? (No hagas cagadas te lo pido por favor) " -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    if ($grabar.toLower() -eq "s"){
        if ($interno -eq 0) {$interno=585} else {$interno=2}
        #Write-Output $interno
        $query ="INSERT INTO dbo.Medicos  (apellido, nombre, documento, hospitalPrincipal, activo,patologo,numeroAgente) VALUES ('$apellido', '$nombre', '$dni', $interno, 1,$pat,'$numeroagente')"
        #Write-Output $query
        insertdb $query
        
    }
}

function actualizarfunciones{
    do{
        $idmedico = Read-Host "Ingrese Id Médico";
        }while (-not ($idmedico -match '^[\d]+$'))
    $data = New-Object System.Data.DataSet
    $data=buscarmedicoporid $idmedico 1
    if ($data.tables[0].Rows.count -eq 0) {exit}
    foreach ($Row in $data.tables[0].Rows){
        Write-Output $Row
    }
    Write-Output "cantidad de resultados" $data.tables[0].Rows.count
    $query = "SELECT idMedico,idFuncion FROM dbo.Medicos_Funciones where idMedico= $idmedico"  
    #Write-Output $query        
    $data=querydb $query    
    foreach ($Row in $data.tables[0].Rows){
        Write-Output $Row
    }
    Write-Output "cantidad de resultados" $data.tables[0].Rows.count
    $Continuar = $(Write-Host "Desea Actualizar Funciones" -NoNewLine) + $(Write-Host "[S/N]" -ForegroundColor yellow -NoNewLine ;Read-Host )
    if ($Continuar.toLower() -eq "s"){
        do{
            $(Write-Host "Elija nueva función" )+$(Write-Host "[1]" -ForegroundColor yellow -NoNewLine)+$(Write-Host " Médico Guardia Pediatrica" ) +
            $(Write-Host "[2]" -ForegroundColor yellow -NoNewLine) + $(Write-Host " Médico Guardia Adultos" ) + 
            $(Write-Host "[3]" -ForegroundColor yellow -NoNewLine) + $(Write-Host " Enfermero" ) +  
            $(Write-Host "[4]" -ForegroundColor yellow -NoNewLine)+ $(Write-Host " Patológo" )  +
            $(Write-Host "[5]" -ForegroundColor yellow -NoNewLine)+ $(Write-Host " Citotécnico" )
            $(Write-Host "[6]" -ForegroundColor yellow -NoNewLine)+ $(Write-Host " CANCELAR"  )
            $funcion= Read-Host 
        }while (-not ($funcion -match '^[1|2|3|4|5|6]$'))
        switch($funcion){
            1{$funcion="emergenciasPediatria";break}
            2{$funcion="emergenciasAdultos";break}
            3{$funcion="enfermero";break}
            4{$funcion="patologo";break}
            5{$funcion="citotecnico";break}
            6{exit}
        }
        foreach ($Row in $data.tables[0].Rows){ #controla que no tenga cargada la función
                if ( $Row["idFuncion"] -eq $funcion){Write-Output "Ya esta cargada la función salamx";exit}
            }
        $query= "INSERT INTO dbo.Medicos_Funciones  (idMedico, idFuncion) VALUES ($idmedico,'$funcion')"
        insertdb $query
    }else {exit}
}
showmenu
 
while(($inp = Read-Host -Prompt "Elegir una Opción") -ne "8"){
 
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
        7 {
            Clear-Host
            Write-Host "------------------------------";
            Write-Host "Actualizar Tabla Médicos_Funciones";
            Write-Host "------------------------------"; 
            actualizarfunciones;
            break
            }                  
        8 {"Exit";  break}
        default {Write-Host -ForegroundColor red -BackgroundColor white "Opción Inválida";pause}
    }
showmenu
}