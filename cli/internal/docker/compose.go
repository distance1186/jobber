package docker

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

// Prerequisite describes a dependency and its status.
type Prerequisite struct {
	Name      string
	Found     bool
	Version   string
	Required  bool
	HelpLinux string
	HelpWin   string
}

// CheckPrerequisites verifies Docker and Docker Compose are installed.
// On Linux it offers to install missing required dependencies automatically.
func CheckPrerequisites() error {
	prereqs := DetectPrerequisites()
	allGood := true

	for _, p := range prereqs {
		if p.Found {
			fmt.Printf("  ✓ %s (%s)\n", p.Name, p.Version)
		} else if p.Required {
			fmt.Printf("  ✗ %s — MISSING (required)\n", p.Name)
			allGood = false
		} else {
			fmt.Printf("  - %s — not found (optional)\n", p.Name)
		}
	}

	if !allGood {
		fmt.Println()
		return promptInstallDeps(prereqs)
	}

	// On Windows, check WSL2
	if runtime.GOOS == "windows" {
		if err := checkWSL2(); err != nil {
			return err
		}
		fmt.Println("  ✓ WSL2")
	}

	// Check docker group membership on Linux
	if runtime.GOOS == "linux" {
		if err := checkDockerGroup(); err != nil {
			fmt.Printf("  ⚠ %s\n", err)
		}
	}

	return nil
}

// DetectPrerequisites returns the status of all dependencies.
func DetectPrerequisites() []Prerequisite {
	prereqs := []Prerequisite{
		{
			Name:      "Docker Engine",
			Required:  true,
			HelpLinux: "curl -fsSL https://get.docker.com | sh",
			HelpWin:   "Download from https://www.docker.com/products/docker-desktop/",
		},
		{
			Name:      "Docker Compose",
			Required:  true,
			HelpLinux: "sudo apt-get install -y docker-compose-plugin",
			HelpWin:   "Included with Docker Desktop",
		},
		{
			Name:      "NVIDIA Container Toolkit",
			Required:  false,
			HelpLinux: "See https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html",
			HelpWin:   "Included with Docker Desktop (requires NVIDIA GPU drivers)",
		},
	}

	// Check Docker
	if out, err := exec.Command("docker", "version", "--format", "{{.Server.Version}}").Output(); err == nil {
		prereqs[0].Found = true
		prereqs[0].Version = strings.TrimSpace(string(out))
	}

	// Check Docker Compose
	if out, err := exec.Command("docker", "compose", "version", "--short").Output(); err == nil {
		prereqs[1].Found = true
		prereqs[1].Version = "v" + strings.TrimSpace(string(out))
	}

	// Check NVIDIA Container Toolkit (only relevant if nvidia-smi exists)
	if _, err := exec.LookPath("nvidia-smi"); err == nil {
		if out, err := exec.Command("nvidia-container-cli", "--version").Output(); err == nil {
			prereqs[2].Found = true
			prereqs[2].Version = strings.TrimSpace(string(out))
		} else if out, err := exec.Command("docker", "info", "--format", "{{range .Runtimes}}{{.Path}} {{end}}").Output(); err == nil && strings.Contains(string(out), "nvidia") {
			prereqs[2].Found = true
			prereqs[2].Version = "detected via docker info"
		}
	} else {
		// No GPU, mark as N/A
		prereqs[2].Found = true
		prereqs[2].Version = "no GPU — not needed"
	}

	return prereqs
}

// promptInstallDeps offers to install missing required dependencies.
func promptInstallDeps(prereqs []Prerequisite) error {
	fmt.Println("Missing required dependencies:")
	for _, p := range prereqs {
		if !p.Found && p.Required {
			if runtime.GOOS == "windows" {
				fmt.Printf("  • %s: %s\n", p.Name, p.HelpWin)
			} else {
				fmt.Printf("  • %s: %s\n", p.Name, p.HelpLinux)
			}
		}
	}

	if runtime.GOOS != "linux" {
		return fmt.Errorf("please install the missing dependencies above and re-run jobber-setup install")
	}

	fmt.Print("\nWould you like to install missing dependencies now? [Y/n] ")
	reader := bufio.NewReader(os.Stdin)
	answer, _ := reader.ReadString('\n')
	answer = strings.TrimSpace(strings.ToLower(answer))
	if answer != "" && answer != "y" && answer != "yes" {
		return fmt.Errorf("please install the missing dependencies and re-run jobber-setup install")
	}

	for _, p := range prereqs {
		if p.Found || !p.Required {
			continue
		}
		fmt.Printf("Installing %s...\n", p.Name)
		switch p.Name {
		case "Docker Engine":
			if err := installDocker(); err != nil {
				return fmt.Errorf("failed to install Docker: %w", err)
			}
		case "Docker Compose":
			if err := installDockerCompose(); err != nil {
				return fmt.Errorf("failed to install Docker Compose: %w", err)
			}
		}
	}

	// Verify after install
	fmt.Println("\nVerifying installation...")
	if _, err := exec.Command("docker", "version").Output(); err != nil {
		return fmt.Errorf("docker still not working — you may need to log out and back in, or run: newgrp docker")
	}
	if _, err := exec.Command("docker", "compose", "version").Output(); err != nil {
		return fmt.Errorf("docker compose still not working after install")
	}
	fmt.Println("  ✓ All required dependencies installed successfully")
	return nil
}

func installDocker() error {
	fmt.Println("  Running: curl -fsSL https://get.docker.com | sh")
	cmd := exec.Command("sh", "-c", "curl -fsSL https://get.docker.com | sh")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}

	// Add current user to docker group
	user := os.Getenv("USER")
	if user != "" && user != "root" {
		fmt.Printf("  Adding user '%s' to docker group...\n", user)
		add := exec.Command("sudo", "usermod", "-aG", "docker", user)
		add.Stdout = os.Stdout
		add.Stderr = os.Stderr
		add.Run() // best-effort
	}

	// Enable and start docker
	exec.Command("sudo", "systemctl", "enable", "docker").Run()
	exec.Command("sudo", "systemctl", "start", "docker").Run()
	return nil
}

func installDockerCompose() error {
	fmt.Println("  Running: sudo apt-get install -y docker-compose-plugin")
	cmd := exec.Command("sudo", "apt-get", "install", "-y", "docker-compose-plugin")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func checkWSL2() error {
	_, err := exec.Command("wsl", "--status").Output()
	if err != nil {
		return fmt.Errorf("WSL2 is required on Windows. Run: wsl --install")
	}
	return nil
}

func checkDockerGroup() error {
	user := os.Getenv("USER")
	if user == "root" {
		return nil
	}
	out, err := exec.Command("groups").Output()
	if err != nil {
		return nil
	}
	if !strings.Contains(string(out), "docker") {
		return fmt.Errorf("user '%s' is not in the docker group — run: sudo usermod -aG docker %s && newgrp docker", user, user)
	}
	return nil
}

func composeCmd(projectDir string, args ...string) *exec.Cmd {
	composePath := filepath.Join(projectDir, "docker-compose.yml")
	fullArgs := append([]string{"compose", "-f", composePath}, args...)
	cmd := exec.Command("docker", fullArgs...)
	cmd.Dir = projectDir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd
}

// ComposeUp starts the Jobber stack.
func ComposeUp(projectDir string) error {
	return composeCmd(projectDir, "up", "-d").Run()
}

// ComposeDown stops the Jobber stack.
func ComposeDown(projectDir string) error {
	return composeCmd(projectDir, "down").Run()
}

// ComposePull pulls latest images.
func ComposePull(projectDir string) error {
	return composeCmd(projectDir, "pull").Run()
}

// ComposeStatus shows container status.
func ComposeStatus(projectDir string) error {
	return composeCmd(projectDir, "ps").Run()
}

// ComposeBuild builds images.
func ComposeBuild(projectDir string) error {
	return composeCmd(projectDir, "up", "-d", "--build").Run()
}
