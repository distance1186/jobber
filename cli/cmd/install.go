package cmd

import (
	"fmt"
	"os"

	"github.com/distance1186/jobber/cli/internal/detect"
	"github.com/distance1186/jobber/cli/internal/docker"
	"github.com/distance1186/jobber/cli/internal/wizard"
	"github.com/spf13/cobra"
)

var installCmd = &cobra.Command{
	Use:   "install",
	Short: "Run the guided installation and configuration wizard",
	RunE:  runInstall,
}

func init() {
	rootCmd.AddCommand(installCmd)
}

func runInstall(cmd *cobra.Command, args []string) error {
	printBanner()

	// Step 1: Check prerequisites
	fmt.Println("[1/4] Checking prerequisites...")
	if err := docker.CheckPrerequisites(); err != nil {
		return fmt.Errorf("prerequisite check failed: %w", err)
	}
	fmt.Println("  ✓ Docker and Docker Compose found")

	// Step 2: Detect hardware
	fmt.Println("[2/4] Detecting hardware...")
	hw := detect.GetHardwareInfo()
	fmt.Printf("  RAM:  %d GB\n", hw.TotalRAMGB)
	fmt.Printf("  CPU:  %d cores\n", hw.CPUCores)
	if hw.GPUName != "" {
		fmt.Printf("  GPU:  %s (%d MB VRAM)\n", hw.GPUName, hw.GPUVRAM)
	} else {
		fmt.Println("  GPU:  None detected")
	}

	// Step 3: Check project directory
	fmt.Println("[3/4] Checking project directory...")
	if _, err := os.Stat(projectDir); os.IsNotExist(err) {
		return fmt.Errorf("directory does not exist: %s", projectDir)
	}
	fmt.Printf("  ✓ Using directory: %s\n", projectDir)

	// Step 4: Launch config wizard
	fmt.Println("[4/4] Launching configuration wizard...")
	fmt.Println("  Opening http://localhost:9898/setup in your browser...")
	return wizard.Serve(projectDir, hw)
}
