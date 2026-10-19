#include "FrogLevelActors.h"

#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "FrogLevelGameMode.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

#define LOCTEXT_NAMESPACE "FrogLevel"

namespace
{
	UPointLightComponent* MakeLight(AActor* Owner, USceneComponent* Parent, FName Name, const FLinearColor& Color, float Lumens, float Radius)
	{
		UPointLightComponent* Light = Owner->CreateDefaultSubobject<UPointLightComponent>(Name);
		Light->SetupAttachment(Parent);
		Light->SetIntensityUnits(ELightUnits::Lumens);
		Light->SetIntensity(Lumens);
		Light->SetLightColor(Color);
		Light->SetAttenuationRadius(Radius);
		return Light;
	}

	UStaticMeshComponent* MakeMesh(AActor* Owner, USceneComponent* Parent, bool bCollide)
	{
		UStaticMeshComponent* Mesh = Owner->CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
		Mesh->SetupAttachment(Parent);
		if (!bCollide)
		{
			Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		}
		return Mesh;
	}

	float EaseOut(float Alpha)
	{
		const float A = FMath::Clamp(Alpha, 0.0f, 1.0f);
		return 1.0f - (1.0f - A) * (1.0f - A);
	}
}

// ---------------------------------------------------------------- trigger

AFrogLevelTrigger::AFrogLevelTrigger()
{
	PrimaryActorTick.bCanEverTick = false;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(RootComponent);
	Trigger->SetBoxExtent(FVector(100.0f));
	Trigger->SetCollisionObjectType(ECC_WorldDynamic);
	Trigger->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Trigger->SetCollisionResponseToAllChannels(ECR_Ignore);
	Trigger->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Trigger->SetGenerateOverlapEvents(true);
	Trigger->SetHiddenInGame(true);
}

void AFrogLevelTrigger::NotifyActorBeginOverlap(AActor* OtherActor)
{
	Super::NotifyActorBeginOverlap(OtherActor);

	ACharacter* Character = Cast<ACharacter>(OtherActor);
	if (Character && Character->IsPlayerControlled())
	{
		OnPlayerEnter(Character);
	}
}

AFrogLevelGameMode* AFrogLevelTrigger::GetFrogGameMode() const
{
	return GetWorld() ? GetWorld()->GetAuthGameMode<AFrogLevelGameMode>() : nullptr;
}

// ---------------------------------------------------------------- fly

AFrogFlyPickup::AFrogFlyPickup()
{
	PrimaryActorTick.bCanEverTick = true;
	Trigger->SetBoxExtent(FVector(55.0f));

	Mesh = MakeMesh(this, RootComponent, false);
	Mesh->SetCastShadow(false);
	Glow = MakeLight(this, RootComponent, TEXT("Glow"), FLinearColor(1.0f, 0.78f, 0.3f), 150.0f, 300.0f);
	Glow->SetCastShadows(false);
}

void AFrogFlyPickup::BeginPlay()
{
	Super::BeginPlay();

	const FVector Location = GetActorLocation();
	Phase = static_cast<float>(Location.X * 0.013 + Location.Y * 0.021);
	MeshBaseLocation = Mesh->GetRelativeLocation();
	MeshBaseScale = Mesh->GetRelativeScale3D();
	GlowBaseIntensity = Glow->Intensity;
}

void AFrogFlyPickup::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	Age += DeltaTime;

	if (!bCollected)
	{
		Mesh->SetRelativeLocation(MeshBaseLocation + FVector(0.0f, 0.0f, FMath::Sin(Age * 2.2f + Phase) * BobHeight));
		Mesh->AddLocalRotation(FRotator(0.0f, SpinSpeed * DeltaTime, 0.0f));
		Glow->SetIntensity(GlowBaseIntensity * (1.0f + 0.15f * FMath::Sin(Age * 5.0f + Phase)));
		return;
	}

	// Caught: swell, rise and flare, then vanish.
	CollectedAge += DeltaTime;
	const float Alpha = FMath::Clamp(CollectedAge / 0.35f, 0.0f, 1.0f);
	Mesh->SetRelativeLocation(MeshBaseLocation + FVector(0.0f, 0.0f, EaseOut(Alpha) * 90.0f));
	Mesh->SetRelativeScale3D(MeshBaseScale * FMath::Max(0.01f, (1.0f + Alpha * 0.8f) * (1.0f - Alpha)));
	Mesh->AddLocalRotation(FRotator(0.0f, SpinSpeed * 6.0f * DeltaTime, 0.0f));
	Glow->SetIntensity(GlowBaseIntensity * 6.0f * (1.0f - Alpha));
	if (Alpha >= 1.0f)
	{
		Destroy();
	}
}

void AFrogFlyPickup::OnPlayerEnter(ACharacter* Player)
{
	if (bCollected)
	{
		return;
	}
	bCollected = true;
	SetActorEnableCollision(false);
	if (AFrogLevelGameMode* GameMode = GetFrogGameMode())
	{
		GameMode->CollectFly(this);
	}
}

// ---------------------------------------------------------------- checkpoint

AFrogCheckpoint::AFrogCheckpoint()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	Trigger->SetBoxExtent(FVector(140.0f, 140.0f, 150.0f));
	Trigger->SetRelativeLocation(FVector(0.0f, 0.0f, 150.0f));

	Mesh = MakeMesh(this, RootComponent, false);
	Light = MakeLight(this, RootComponent, TEXT("Light"), IdleColor, 300.0f, 700.0f);
	Light->SetRelativeLocation(FVector(0.0f, 0.0f, 150.0f));
	Light->SetCastShadows(false);
}

FTransform AFrogCheckpoint::GetRespawnTransform() const
{
	return FTransform(FRotator(0.0f, GetActorRotation().Yaw, 0.0f), GetActorLocation() + FVector(0.0f, 0.0f, RespawnHeight));
}

void AFrogCheckpoint::OnPlayerEnter(ACharacter* Player)
{
	if (!bActive)
	{
		bActive = true;
		ActiveAge = 0.0f;
		IdleIntensity = Light->Intensity;
		SetActorTickEnabled(true);
	}
	if (AFrogLevelGameMode* GameMode = GetFrogGameMode())
	{
		GameMode->ActivateCheckpoint(this);
	}
}

void AFrogCheckpoint::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Flare past the lit brightness, then settle on it in the warm colour.
	ActiveAge += DeltaTime;
	const float Alpha = FMath::Clamp(ActiveAge / 0.8f, 0.0f, 1.0f);
	const float Flare = FMath::Sin(Alpha * PI) * 1.5f;
	Light->SetLightColor(FMath::Lerp(IdleColor, ActiveColor, EaseOut(Alpha * 2.0f)));
	Light->SetIntensity(FMath::Lerp(IdleIntensity, ActiveIntensity, EaseOut(Alpha)) * (1.0f + Flare));
	if (Alpha >= 1.0f)
	{
		SetActorTickEnabled(false);
	}
}

// ---------------------------------------------------------------- goal

AFrogGoal::AFrogGoal()
{
	PrimaryActorTick.bCanEverTick = true;
	Trigger->SetBoxExtent(FVector(220.0f, 220.0f, 200.0f));
	Trigger->SetRelativeLocation(FVector(0.0f, 0.0f, 200.0f));

	Mesh = MakeMesh(this, RootComponent, true);
	Beacon = MakeLight(this, RootComponent, TEXT("Beacon"), FLinearColor(1.0f, 0.58f, 0.22f), 600.0f, 2500.0f);
	Beacon->SetRelativeLocation(FVector(0.0f, 0.0f, 260.0f));
}

void AFrogGoal::BeginPlay()
{
	Super::BeginPlay();
	UnlitIntensity = Beacon->Intensity;
}

void AFrogGoal::OnPlayerEnter(ACharacter* Player)
{
	if (bLit)
	{
		return;
	}
	bLit = true;
	LitAge = 0.0f;
	if (AFrogLevelGameMode* GameMode = GetFrogGameMode())
	{
		GameMode->CompleteLevel();
	}
}

void AFrogGoal::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// A soft flicker before and after, ramping up to the lit brightness when reached.
	LitAge += DeltaTime;
	const float Target = bLit ? FMath::Lerp(UnlitIntensity, LitIntensity, EaseOut(LitAge / FMath::Max(LightUpTime, 0.01f))) : UnlitIntensity;
	const float Flicker = 1.0f + 0.06f * FMath::Sin(LitAge * 13.0f) + 0.04f * FMath::Sin(LitAge * 7.3f + 1.0f);
	Beacon->SetIntensity(Target * Flicker);
}

// ---------------------------------------------------------------- bounce

AFrogBouncePad::AFrogBouncePad()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	Trigger->SetBoxExtent(FVector(70.0f, 70.0f, 25.0f));

	Mesh = MakeMesh(this, RootComponent, true);
}

void AFrogBouncePad::BeginPlay()
{
	Super::BeginPlay();
	MeshBaseScale = Mesh->GetRelativeScale3D();
}

void AFrogBouncePad::OnPlayerEnter(ACharacter* Player)
{
	// Only when landing or walking on, not while already flying up through the cap.
	if (Player->GetVelocity().Z > 100.0f)
	{
		return;
	}
	Player->LaunchCharacter(FVector(0.0f, 0.0f, LaunchSpeed), false, true);
	SquashAge = 0.0f;
	SetActorTickEnabled(true);
}

void AFrogBouncePad::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Squash and wobble back, about a second.
	SquashAge += DeltaTime;
	const float Wobble = FMath::Exp(-5.0f * SquashAge) * FMath::Cos(16.0f * SquashAge);
	Mesh->SetRelativeScale3D(MeshBaseScale * FVector(1.0f + 0.12f * Wobble, 1.0f + 0.12f * Wobble, 1.0f - 0.22f * Wobble));
	if (SquashAge > 1.0f)
	{
		Mesh->SetRelativeScale3D(MeshBaseScale);
		SetActorTickEnabled(false);
	}
}

// ---------------------------------------------------------------- hazards and hints

void AFrogRespawnVolume::OnPlayerEnter(ACharacter* Player)
{
	if (AFrogLevelGameMode* GameMode = GetFrogGameMode())
	{
		GameMode->RespawnPlayer(Message.IsEmpty() ? LOCTEXT("Ouch", "Ouch!") : Message);
	}
}

void AFrogHintVolume::OnPlayerEnter(ACharacter* Player)
{
	if (bShown)
	{
		return;
	}
	bShown = true;
	if (AFrogLevelGameMode* GameMode = GetFrogGameMode())
	{
		GameMode->ShowToast(Message, Duration);
	}
}

#undef LOCTEXT_NAMESPACE
