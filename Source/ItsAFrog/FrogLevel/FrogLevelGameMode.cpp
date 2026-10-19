#include "FrogLevelGameMode.h"

#include "Camera/PlayerCameraManager.h"
#include "EngineUtils.h"
#include "FrogLevelActors.h"
#include "FrogLevelHUD.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "ItsAFrog.h"

#define LOCTEXT_NAMESPACE "FrogLevel"

AFrogLevelGameMode::AFrogLevelGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	HUDClass = AFrogLevelHUD::StaticClass();
}

void AFrogLevelGameMode::BeginPlay()
{
	Super::BeginPlay();

	StartTime = Now();
	for (TActorIterator<AFrogFlyPickup> It(GetWorld()); It; ++It)
	{
		++FliesTotal;
	}
	UE_LOG(LogItsAFrog, Log, TEXT("Frog level '%s' started with %d golden flies."), *LevelTitle.ToString(), FliesTotal);
}

void AFrogLevelGameMode::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	const APlayerController* PlayerController = GetWorld()->GetFirstPlayerController();
	const APawn* Pawn = PlayerController ? PlayerController->GetPawn() : nullptr;
	if (!Pawn)
	{
		return;
	}

	// Until the first checkpoint, the player comes back to where they started.
	if (!bHasRespawn)
	{
		RespawnTransform = Pawn->GetActorTransform();
		bHasRespawn = true;
	}

	if (Pawn->GetActorLocation().Z < RespawnZ)
	{
		RespawnPlayer(LOCTEXT("Splash", "Splash!"));
	}
}

float AFrogLevelGameMode::Now() const
{
	return GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
}

float AFrogLevelGameMode::GetRunTime() const
{
	return (bLevelComplete ? FinishTime : Now()) - StartTime;
}

float AFrogLevelGameMode::GetLevelAge() const
{
	return Now() - StartTime;
}

void AFrogLevelGameMode::CollectFly(AFrogFlyPickup* Fly)
{
	++FliesCollected;
	LastFlyTime = Now();
	if (FliesCollected == FliesTotal)
	{
		ShowToast(LOCTEXT("AllFlies", "Every golden fly caught!"), 3.0f);
	}
	UE_LOG(LogItsAFrog, Log, TEXT("Caught %s (%d/%d)."), *GetNameSafe(Fly), FliesCollected, FliesTotal);
}

void AFrogLevelGameMode::ActivateCheckpoint(AFrogCheckpoint* Checkpoint)
{
	if (!Checkpoint || Checkpoint == CurrentCheckpoint)
	{
		return;
	}
	// Walking back to an earlier checkpoint makes it the respawn point again, quietly.
	CurrentCheckpoint = Checkpoint;
	RespawnTransform = Checkpoint->GetRespawnTransform();
	bHasRespawn = true;
	bool bAlreadyReached = false;
	ReachedCheckpoints.Add(Checkpoint, &bAlreadyReached);
	if (!bAlreadyReached)
	{
		ShowToast(LOCTEXT("Checkpoint", "Checkpoint!"), 2.0f);
		UE_LOG(LogItsAFrog, Log, TEXT("Checkpoint %s reached."), *GetNameSafe(Checkpoint));
	}
}

void AFrogLevelGameMode::CompleteLevel()
{
	if (bLevelComplete)
	{
		return;
	}
	bLevelComplete = true;
	FinishTime = Now();
	UE_LOG(LogItsAFrog, Log, TEXT("Level complete in %.1f s with %d/%d flies and %d splashes."), GetRunTime(), FliesCollected, FliesTotal, Splashes);
}

void AFrogLevelGameMode::RespawnPlayer(const FText& Message)
{
	APlayerController* PlayerController = GetWorld()->GetFirstPlayerController();
	APawn* Pawn = PlayerController ? PlayerController->GetPawn() : nullptr;
	if (!Pawn || !bHasRespawn || Now() - LastRespawnTime < 0.5f)
	{
		return;
	}
	LastRespawnTime = Now();
	++Splashes;

	if (ACharacter* Character = Cast<ACharacter>(Pawn))
	{
		Character->GetCharacterMovement()->StopMovementImmediately();
	}
	Pawn->TeleportTo(RespawnTransform.GetLocation(), RespawnTransform.Rotator(), false, true);
	if (PlayerController->PlayerCameraManager)
	{
		PlayerController->PlayerCameraManager->StartCameraFade(1.0f, 0.0f, 0.6f, FLinearColor(0.01f, 0.02f, 0.06f), false, false);
	}
	ShowToast(Message, 1.5f);
}

void AFrogLevelGameMode::ShowToast(const FText& Text, float Duration)
{
	ToastText = Text;
	ToastTime = Now();
	ToastDuration = Duration;
}

const FText& AFrogLevelGameMode::GetToast(float& OutAge, float& OutDuration) const
{
	OutAge = Now() - ToastTime;
	OutDuration = ToastDuration;
	return ToastText;
}

#undef LOCTEXT_NAMESPACE
