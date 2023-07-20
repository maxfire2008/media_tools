param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$VideoPath,

    [Parameter(Mandatory = $true, Position = 1)]
    [int]$TargetFileSizeMB
)

# Define the path to your FFmpeg executable
$ffmpegPath = "C:\bin\ffmpeg.exe"

# Function to get the duration of the video using FFmpeg
function GetVideoDuration($videoPath) {
    $ffmpegOutput = & $ffmpegPath -i $videoPath 2>&1
    $durationLine = $ffmpegOutput | Where-Object { $_ -match 'Duration: (\d+):(\d+):(\d+.\d+)' }
    if ($durationLine) {
        $hours = [int]$matches[1]
        $minutes = [int]$matches[2]
        $seconds = [double]$matches[3]
        $totalSeconds = $hours * 3600 + $minutes * 60 + $seconds
        return $totalSeconds
    }
    return $null
}

# Function to calculate the new width and height while maintaining the aspect ratio
function GetNewResolution($width, $height, $maxWidth, $maxHeight) {
    $aspectWidth = $maxHeight * $width / $height
    $aspectHeight = $maxWidth * $height / $width

    if ($aspectWidth -ge $maxWidth) {
        return $maxWidth, $aspectHeight
    }
    else {
        return $aspectWidth, $maxHeight
    }
}

# Function to get video information using ffprobe
function GetVideoInfo($inputPath) {
    $ffprobePath = "ffprobe"
    $ffprobeArgs = "-v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of default=noprint_wrappers=1:nokey=1"

    $cmd = "& $ffprobePath $ffprobeArgs `"$inputPath`""
    $output = Invoke-Expression $cmd 2>&1

    $videoInfo = $output -split '\s+'

    if ($videoInfo.Count -eq 3) {
        $width = [int]$videoInfo[0]
        $height = [int]$videoInfo[1]
        $numerator = $videoInfo[2]
        $denominator = 1  # Default denominator in case r_frame_rate is a whole number
        if ($numerator -contains "/") {
            $numerator, $denominator = $numerator -split '/'
        }
        $frameRate = [double]([int]$numerator / [int]$denominator)
        return $width, $height, $frameRate
    }

    return $null
}

# Function to compress the video using FFmpeg with H.264 codec, capped frame rate, and resolution
function CompressVideo($inputPath, $outputPath, $targetFileSizeMB) {
    $maxWidth = 1280
    $maxHeight = 720
    $maxFrameRate = 25

    $videoInfo = GetVideoInfo $inputPath
    if (-not $videoInfo) {
        Write-Host "Failed to get video information. Compression aborted."
        exit
    }

    $width, $height, $frameRate = $videoInfo
    Write-Output $frameRate

    $newWidth, $newHeight = GetNewResolution $width $height $maxWidth $maxHeight
    $newFrameRate = [math]::Min($frameRate, $maxFrameRate)

    $vfFilter = "scale=$newWidth`:$newHeight"
    & $ffmpegPath -i $inputPath -c:v libx264 -r $newFrameRate -vf $vfFilter -b:v 0 -c:a copy $outputPath
}




# Check if the video file exists
if (-not (Test-Path $VideoPath)) {
    Write-Host "The provided video file doesn't exist."
    exit
}

# Get video duration
$duration = GetVideoDuration $VideoPath
if (-not $duration) {
    Write-Host "Failed to get video duration."
    exit
}

# Calculate the target bitrate based on the desired file size
$targetBitrate = $TargetFileSizeMB * 8000 / $duration

# Compress the video and save it to a new file
$newVideoPath = [System.IO.Path]::ChangeExtension($VideoPath, "_compressed.mp4")
CompressVideo $VideoPath $newVideoPath $targetBitrate

# Check the new file size and notify the user
$newFileSize = (Get-Item $newVideoPath).Length
Write-Host "Compression complete!"
Write-Host "Original video duration: $duration seconds"
Write-Host "Target file size: $TargetFileSizeMB MB"
Write-Host "Compressed file size: $(Get-FileLength $newFileSize)"
Write-Host "New video saved to: $newVideoPath"

# Function to convert file size to a human-readable format
function Get-FileLength($length) {
    $unit = "B", "KB", "MB", "GB", "TB" | ForEach-Object {
        if ($length -lt 1KB) { break }
        $length /= 1KB
    }
    return "{0:N2} {1}" -f $length, $unit
}
