package docker

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

// CheckPrerequisites verifies Docker and Docker Compose are installed.
func CheckPrerequisites() error {
	// Check docker
	if _, err := exec.LookPath("docker"); err != nil {
		if runtime.GOOS == "windows" {
			return fmt.Errorf("Docker Desktop not found. Install from https://www.docker.com/products/docker-desktop/")
		}
		return fmt.Errorf("docker not found. Install with: curl -fsSL https://get.docker.com | sh")
	}

	// Check docker compose
	out, err := exec.Command("docker", "compose", "version").Output()
	if err != nil {
		return fmt.Errorf("docker compose not found. Install docker-compose-plugin")
	}
	fmt.Printf("  Found: %s", string(out))

	// On Windows, check WSL2
	if runtime.GOOS == "windows" {
		if err := checkWSL2(); err != nil {
			return err
		}
	}

	return nil
}

func checkWSL2() error {
	_, err := exec.Command("wsl", "--status").Output()
	if err != nil {
		return fmt.Errorf("WSL2 is required on Windows. Run: wsl --install")
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
