package cmd

import (
	"fmt"

	"github.com/distance1186/jobber/cli/internal/detect"
	"github.com/distance1186/jobber/cli/internal/docker"
	"github.com/distance1186/jobber/cli/internal/wizard"
	"github.com/spf13/cobra"
)

var startCmd = &cobra.Command{
	Use:   "start",
	Short: "Start the Jobber stack",
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Println("Starting Jobber stack...")
		return docker.ComposeUp(projectDir)
	},
}

var stopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop the Jobber stack",
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Println("Stopping Jobber stack...")
		return docker.ComposeDown(projectDir)
	},
}

var restartCmd = &cobra.Command{
	Use:   "restart",
	Short: "Restart the Jobber stack",
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Println("Restarting Jobber stack...")
		if err := docker.ComposeDown(projectDir); err != nil {
			return err
		}
		return docker.ComposeUp(projectDir)
	},
}

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show Jobber stack status",
	RunE: func(cmd *cobra.Command, args []string) error {
		printBanner()
		return docker.ComposeStatus(projectDir)
	},
}

var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "Pull latest images and restart",
	RunE: func(cmd *cobra.Command, args []string) error {
		fmt.Println("Pulling latest images...")
		if err := docker.ComposePull(projectDir); err != nil {
			return err
		}
		fmt.Println("Restarting with updated images...")
		return docker.ComposeUp(projectDir)
	},
}

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Re-run the configuration wizard",
	RunE: func(cmd *cobra.Command, args []string) error {
		printBanner()
		hw := detect.GetHardwareInfo()
		return wizard.Serve(projectDir, hw)
	},
}

func init() {
	rootCmd.AddCommand(startCmd)
	rootCmd.AddCommand(stopCmd)
	rootCmd.AddCommand(restartCmd)
	rootCmd.AddCommand(statusCmd)
	rootCmd.AddCommand(updateCmd)
	rootCmd.AddCommand(configCmd)
}
