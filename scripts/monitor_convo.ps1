# Get the PID of the Python process using GPU via nvidia-smi
$nvidiaOutput = & nvidia-smi | findstr python

if ($nvidiaOutput) {
    # Extract the PID (assumes it's the 5th column in nvidia-smi output)
    $columns = $nvidiaOutput -split '\s+'

    Write-Host "PID:"($columns[4])

    while ($true) {
        try {
            $p = Get-Process -Id $columns[4]

            $cpu = $p.CPU
            $ram = [math]::Round($p.WorkingSet64 / 1MB, 2)
            $private = [math]::Round($p.PrivateMemorySize64 / 1MB, 2)
            $virtMB = [math]::Round($p.VirtualMemorySize64 / 1MB, 2)

            Write-Host "CPU: $cpu | RAM: $ram MB | Private: $private MB | Virtual: $virtMB MB"

        } catch {
            Write-Host "Process with PID $pid no longer exists."
            break
        }

        Start-Sleep -Seconds 2
    }
} else {
    Write-Host "No Python process found using the GPU (via nvidia-smi)."
}
