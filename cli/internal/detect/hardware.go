package detect

import (
	"os"
	"os/exec"
	"path/filepath"
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

// detectGPU checks for NVIDIA GPU first, then falls back to
// platform-specific detection for AMD / Intel / other GPUs.
func detectGPU() (string, int64) {
	// NVIDIA — nvidia-smi gives the most accurate results.
	if name, vram := detectNVIDIAGPU(); name != "" {
		return name, vram
	}
	// Fallback to generic detection.
	if runtime.GOOS == "windows" {
		return detectGPUWindows()
	}
	return detectGPULinux()
}

// detectNVIDIAGPU queries nvidia-smi for GPU name and VRAM.
func detectNVIDIAGPU() (string, int64) {
	data, err := exec.Command("nvidia-smi",
		"--query-gpu=name,memory.total",
		"--format=csv,noheader,nounits").Output()
	if err != nil {
		return "", 0
	}
	line := strings.TrimSpace(string(data))
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

// detectGPUWindows uses PowerShell + WMI to find discrete GPUs (AMD, Intel, etc.).
// Note: Win32_VideoController.AdapterRAM is a uint32 so VRAM is capped at ~4 GB.
// The GPU name is always accurate and is the primary value for the user.
func detectGPUWindows() (string, int64) {
	data, err := exec.Command("powershell", "-NoProfile", "-Command",
		`Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + '|' + $_.AdapterRAM }`).Output()
	if err != nil {
		return "", 0
	}
	var bestName string
	var bestRAM int64
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, "|", 2)
		if len(parts) < 2 {
			continue
		}
		name := strings.TrimSpace(parts[0])
		lower := strings.ToLower(name)
		// Skip virtual / generic display adapters.
		if strings.Contains(lower, "microsoft") || strings.Contains(lower, "basic display") {
			continue
		}
		ramBytes, _ := strconv.ParseInt(strings.TrimSpace(parts[1]), 10, 64)
		ramMB := ramBytes / 1024 / 1024
		if ramMB > bestRAM || bestName == "" {
			bestName = name
			bestRAM = ramMB
		}
	}
	return bestName, bestRAM
}

// detectGPULinux uses lspci to find GPUs and sysfs to read AMD VRAM.
func detectGPULinux() (string, int64) {
	data, err := exec.Command("lspci").Output()
	if err != nil {
		return "", 0
	}
	var gpuName string
	for _, line := range strings.Split(string(data), "\n") {
		lower := strings.ToLower(line)
		if !strings.Contains(lower, "vga") && !strings.Contains(lower, "3d controller") {
			continue
		}
		// Format: "06:00.0 VGA compatible controller: AMD/ATI ..."
		parts := strings.SplitN(line, ": ", 2)
		if len(parts) < 2 {
			continue
		}
		name := strings.TrimSpace(parts[1])
		// Prefer discrete GPU over integrated Intel.
		nameLower := strings.ToLower(name)
		if gpuName == "" || !strings.Contains(nameLower, "intel") {
			gpuName = name
		}
	}
	if gpuName == "" {
		return "", 0
	}
	vram := detectAMDVRAMLinux()
	return gpuName, vram
}

// detectAMDVRAMLinux reads VRAM from the amdgpu sysfs interface.
func detectAMDVRAMLinux() int64 {
	matches, err := filepath.Glob("/sys/class/drm/card*/device/mem_info_vram_total")
	if err != nil || len(matches) == 0 {
		return 0
	}
	data, err := os.ReadFile(matches[0])
	if err != nil {
		return 0
	}
	bytes, _ := strconv.ParseInt(strings.TrimSpace(string(data)), 10, 64)
	return bytes / 1024 / 1024 // bytes → MB
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
