package detect

import (
	"os/exec"
	"runtime"
	"strconv"
	"strings"
)

// HardwareInfo holds detected system specs.
type HardwareInfo struct {
	TotalRAMGB int64  `json:"total_ram_gb"`
	CPUCores   int    `json:"cpu_cores"`
	GPUName    string `json:"gpu_name"`
	GPUVRAM    int64  `json:"gpu_vram_mb"` // in MB
	FreeDiskGB int64  `json:"free_disk_gb"`
	OS         string `json:"os"` // "linux" or "windows"
}

// GetHardwareInfo detects system hardware specs.
func GetHardwareInfo() HardwareInfo {
	hw := HardwareInfo{
		CPUCores: runtime.NumCPU(),
		OS:       runtime.GOOS,
	}
	hw.TotalRAMGB = detectRAM()
	hw.GPUName, hw.GPUVRAM = detectGPU()
	hw.FreeDiskGB = detectDisk()
	return hw
}

// detectRAM reads total system memory.
func detectRAM() int64 {
	if runtime.GOOS == "linux" {
		return detectRAMLinux()
	}
	return detectRAMWindows()
}

func detectRAMLinux() int64 {
	data, err := exec.Command("grep", "MemTotal", "/proc/meminfo").Output()
	if err != nil {
		return 0
	}
	// Format: "MemTotal:       65596504 kB"
	fields := strings.Fields(string(data))
	if len(fields) < 2 {
		return 0
	}
	kb, err := strconv.ParseInt(fields[1], 10, 64)
	if err != nil {
		return 0
	}
	return kb / 1024 / 1024 // kB → GB
}

func detectRAMWindows() int64 {
	data, err := exec.Command("wmic", "ComputerSystem", "get", "TotalPhysicalMemory", "/value").Output()
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "TotalPhysicalMemory=") {
			val := strings.TrimPrefix(line, "TotalPhysicalMemory=")
			bytes, err := strconv.ParseInt(val, 10, 64)
			if err != nil {
				return 0
			}
			return bytes / 1024 / 1024 / 1024 // bytes → GB
		}
	}
	return 0
}

// detectGPU checks for NVIDIA GPU via nvidia-smi.
func detectGPU() (string, int64) {
	data, err := exec.Command("nvidia-smi",
		"--query-gpu=name,memory.total",
		"--format=csv,noheader,nounits").Output()
	if err != nil {
		return "", 0
	}
	line := strings.TrimSpace(string(data))
	// May have multiple GPUs; take the first line
	lines := strings.Split(line, "\n")
	if len(lines) == 0 {
		return "", 0
	}
	parts := strings.SplitN(lines[0], ",", 2)
	if len(parts) < 2 {
		return strings.TrimSpace(parts[0]), 0
	}
	name := strings.TrimSpace(parts[0])
	vram, _ := strconv.ParseInt(strings.TrimSpace(parts[1]), 10, 64)
	return name, vram
}

// detectDisk gets free disk space at the current directory.
func detectDisk() int64 {
	if runtime.GOOS == "linux" {
		return detectDiskLinux()
	}
	return detectDiskWindows()
}

func detectDiskLinux() int64 {
	data, err := exec.Command("df", "-BG", "--output=avail", ".").Output()
	if err != nil {
		return 0
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) < 2 {
		return 0
	}
	val := strings.TrimSpace(lines[1])
	val = strings.TrimSuffix(val, "G")
	gb, _ := strconv.ParseInt(val, 10, 64)
	return gb
}

func detectDiskWindows() int64 {
	data, err := exec.Command("wmic", "logicaldisk", "where", "DeviceID='C:'",
		"get", "FreeSpace", "/value").Output()
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "FreeSpace=") {
			val := strings.TrimPrefix(line, "FreeSpace=")
			bytes, _ := strconv.ParseInt(val, 10, 64)
			return bytes / 1024 / 1024 / 1024
		}
	}
	return 0
}
