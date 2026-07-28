// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class ItsAFrog : ModuleRules
{
	public ItsAFrog(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"AnimGraphRuntime",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"ItsAFrog",
			"ItsAFrog/Variant_Platforming",
			"ItsAFrog/Variant_Platforming/Animation",
			"ItsAFrog/Variant_Combat",
			"ItsAFrog/Variant_Combat/AI",
			"ItsAFrog/Variant_Combat/Animation",
			"ItsAFrog/Variant_Combat/Gameplay",
			"ItsAFrog/Variant_Combat/Interfaces",
			"ItsAFrog/Variant_Combat/UI",
			"ItsAFrog/Variant_SideScrolling",
			"ItsAFrog/Variant_SideScrolling/AI",
			"ItsAFrog/Variant_SideScrolling/Gameplay",
			"ItsAFrog/Variant_SideScrolling/Interfaces",
			"ItsAFrog/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
