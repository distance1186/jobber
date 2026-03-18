package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var projectDir string

var rootCmd = &cobra.Command{
	Use:   "jobber-setup",
	Short: "Jobber — Job Aggregation & Tracking System",
	Long:  "Setup, configure, and manage the Jobber self-hosted job tracking stack.",
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&projectDir, "dir", "d", ".", "Jobber project directory")
}

func Execute() error {
	return rootCmd.Execute()
}

func printBanner() {
	fmt.Println(`
     ╦╔═╗╔╗ ╔╗ ╔═╗╦═╗
     ║║ ║╠╩╗╠╩╗║╣ ╠╦╝
    ╚╝╚═╝╚═╝╚═╝╚═╝╩╚═
    Job Aggregation & Tracking System
	`)
}
