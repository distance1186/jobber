package recommend

import "github.com/distance1186/jobber/cli/internal/detect"

// ModelOption describes a recommended LLM model.
type ModelOption struct {
	Name        string `json:"name"`
	DisplayName string `json:"display_name"`
	Params      string `json:"params"`
	PullCmd     string `json:"pull_cmd"`
	RAMGB       int    `json:"ram_gb"`  // minimum RAM needed
	Tier        string `json:"tier"`    // "minimum", "recommended", "best"
	Note        string `json:"note"`
}

// AllModels is the full list of supported models.
var AllModels = []ModelOption{
	{
		Name: "phi4-mini", DisplayName: "Phi-4 Mini", Params: "3.8B",
		PullCmd: "ollama pull phi4-mini", RAMGB: 4, Tier: "minimum",
		Note: "Runs on 8 GB RAM. Lightweight but capable for classification tasks.",
	},
	{
		Name: "qwen3:4b", DisplayName: "Qwen 3 4B", Params: "4B",
		PullCmd: "ollama pull qwen3:4b", RAMGB: 4, Tier: "minimum",
		Note: "Excellent quality for its size. Good alternative to Phi-4 Mini.",
	},
	{
		Name: "mistral-small3", DisplayName: "Mistral Small 3", Params: "7B",
		PullCmd: "ollama pull mistral-small3", RAMGB: 8, Tier: "recommended",
		Note: "Best balance of quality and speed for 16 GB systems.",
	},
	{
		Name: "qwen2.5-coder:7b", DisplayName: "Qwen 2.5 Coder 7B", Params: "7B",
		PullCmd: "ollama pull qwen2.5-coder:7b", RAMGB: 8, Tier: "recommended",
		Note: "Strong at structured output (JSON). Great for classification.",
	},
	{
		Name: "llama3.3", DisplayName: "Llama 3.3 8B", Params: "8B",
		PullCmd: "ollama pull llama3.3", RAMGB: 16, Tier: "recommended",
		Note: "Most popular open model. Recommended default for 16+ GB systems.",
	},
	{
		Name: "gemma3:12b", DisplayName: "Gemma 3 12B", Params: "12B",
		PullCmd: "ollama pull gemma3:12b", RAMGB: 24, Tier: "best",
		Note: "Best quality for systems with 32+ GB RAM or 12+ GB VRAM.",
	},
}

// Recommendation holds the recommendation result for a system.
type Recommendation struct {
	Primary     ModelOption   `json:"primary"`
	Alternatives []ModelOption `json:"alternatives"`
	Warning     string        `json:"warning,omitempty"`
}

// ForHardware returns model recommendations based on detected hardware.
func ForHardware(hw detect.HardwareInfo) Recommendation {
	ram := hw.TotalRAMGB
	vram := hw.GPUVRAM

	rec := Recommendation{}

	switch {
	case ram >= 32 || vram >= 12000:
		rec.Primary = findModel("gemma3:12b")
		rec.Alternatives = []ModelOption{findModel("llama3.3"), findModel("mistral-small3")}
	case ram >= 16 || vram >= 8000:
		rec.Primary = findModel("llama3.3")
		rec.Alternatives = []ModelOption{findModel("mistral-small3"), findModel("qwen2.5-coder:7b")}
	case ram >= 8:
		rec.Primary = findModel("mistral-small3")
		rec.Alternatives = []ModelOption{findModel("qwen2.5-coder:7b"), findModel("phi4-mini")}
	default:
		rec.Primary = findModel("phi4-mini")
		rec.Alternatives = []ModelOption{findModel("qwen3:4b")}
		rec.Warning = "Low RAM detected. LLM inference will be slow. Consider upgrading to 16+ GB."
	}

	return rec
}

func findModel(name string) ModelOption {
	for _, m := range AllModels {
		if m.Name == name {
			return m
		}
	}
	return AllModels[0]
}
