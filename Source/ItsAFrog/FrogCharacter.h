// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "FrogCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class USkeletalMeshComponent;
class UInputAction;
class UInputMappingContext;
class UPrimitiveComponent;
class USkeletalMesh;
class UAnimSequence;
struct FInputActionValue;
class UTongueAnimInstance;

UENUM(BlueprintType)
enum class ETongueState : uint8
{
	Hidden,
	Extending,
	Attached,
	Retracting,
	Cooldown
};

UCLASS()
class ITSAFROG_API AFrogCharacter : public ACharacter
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta=(AllowPrivateAccess="true"))
	USpringArmComponent* CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta=(AllowPrivateAccess="true"))
	UCameraComponent* FollowCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Components", meta=(AllowPrivateAccess="true"))
	TObjectPtr<USkeletalMeshComponent> TongueMesh;

protected:
	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* JumpAction;

	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* MoveAction;

	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* LookAction;

	UPROPERTY(EditAnywhere, Category="Input")
	UInputAction* MouseLookAction;

	/** Axis1D zoom (positive zooms in). When unset, one is created at runtime. Mouse wheel and gamepad shoulders are mapped to it either way. */
	UPROPERTY(EditAnywhere, Category="Input")
	TObjectPtr<UInputAction> ZoomAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Input")
	TObjectPtr<UInputAction> TongueAction;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration")
	FName TongueSocketName = TEXT("TongueSocket");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="1.0", Units="cm"))
	float MaximumTongueLength = 500.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="cm"))
	float TraceRadius = 20.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.001", Units="s"))
	float ExtensionDuration = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.001", Units="s"))
	float RetractionDuration = 0.18f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="s"))
	float MaximumAttachedDuration = 0.75f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="s"))
	float CooldownDuration = 0.20f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.0", Units="cm"))
	float ArcHeight = 35.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(Units="cm"))
	float SideArcOffset = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration", meta=(ClampMin="0.1"))
	float EasingExponent = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Configuration")
	TEnumAsByte<ECollisionChannel> TongueTraceChannel = ECC_Visibility;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Debug")
	bool bDrawTongueDebug = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Tongue|Debug", meta=(ClampMin="0.0", Units="s"))
	float DebugDrawDuration = 0.0f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Tongue|State")
	ETongueState TongueState = ETongueState::Hidden;

public:
	/** High three-quarter "diorama" camera instead of the free orbit camera; look input turns and tilts it around the frog. Movement follows the camera's yaw. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama")
	bool bUseDioramaCamera = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="-89.0", ClampMax="-5.0", Units="deg"))
	float DioramaPitch = -40.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", Units="deg"))
	float DioramaYaw = 45.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="100.0", Units="cm"))
	float DioramaArmLength = 1500.0f;

	/** Closest and farthest the zoom input can bring the diorama camera. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="100.0", Units="cm"))
	float DioramaMinArmLength = 600.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="100.0", Units="cm"))
	float DioramaMaxArmLength = 3000.0f;

	/** Arm length change per mouse-wheel notch (gamepad shoulders zoom at about eight notches a second). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="0.0", Units="cm"))
	float DioramaZoomStep = 150.0f;

	/** How quickly the camera eases to the zoomed arm length. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="0.0"))
	float DioramaZoomSpeed = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="5.0", ClampMax="170.0", Units="deg"))
	float DioramaFieldOfView = 35.0f;

	/** How much horizontal look input turns the diorama camera around the frog. 0 locks the angle. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="0.0"))
	float DioramaTurnScale = 1.0f;

	/** How much vertical look input tilts the diorama camera between DioramaMinPitch and DioramaMaxPitch. 0 locks the tilt. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="0.0"))
	float DioramaTiltScale = 1.0f;

	/** Reverses horizontal look input on the diorama camera (the direction it turns around the frog). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera"))
	bool bInvertDioramaTurn = false;

	/** Reverses vertical look input on the diorama camera (the direction it tilts between top-down and the horizon). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera"))
	bool bInvertDioramaTilt = true;

	/** Steepest (most top-down) and flattest tilt the look input can give the diorama camera. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="-89.0", ClampMax="-5.0", Units="deg"))
	float DioramaMinPitch = -75.0f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Camera|Diorama", meta=(EditCondition="bUseDioramaCamera", ClampMin="-89.0", ClampMax="-5.0", Units="deg"))
	float DioramaMaxPitch = -10.0f;

	/** When set, replaces the mesh component's skeletal mesh and fits the capsule to it (feet at the mesh origin). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Stylized")
	TObjectPtr<USkeletalMesh> StylizedMesh;

	/** Yaw applied to StylizedMesh so its front faces the actor's forward (+X). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Stylized", meta=(Units="deg"))
	float StylizedMeshYaw = 0.0f;

	/** Capsule height for StylizedMesh. 0 fits it to the mesh's bounds, which come out too small for meshes whose skeleton carries the scale (the packaged frog's bounds read 1 cm, for a 20 cm capsule). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Stylized", meta=(ClampMin="0.0", Units="cm"))
	float StylizedCapsuleHeight = 0.0f;

	/** Capsule radius for StylizedMesh. 0 derives it from the mesh's bounds. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Stylized", meta=(ClampMin="0.0", Units="cm"))
	float StylizedCapsuleRadius = 0.0f;

	/** Speed-picked clips played when the mesh has no Animation Blueprint. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Locomotion")
	TObjectPtr<UAnimSequence> IdleAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Locomotion")
	TObjectPtr<UAnimSequence> WalkAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Locomotion")
	TObjectPtr<UAnimSequence> RunAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Character|Locomotion", meta=(ClampMin="0.0", Units="cm/s"))
	float RunSpeedThreshold = 350.0f;

protected:
	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void Zoom(const FInputActionValue& Value);

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoMove(float Right, float Forward);

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoLook(float Yaw, float Pitch);

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoJumpStart();

	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoJumpEnd();

	UFUNCTION(BlueprintCallable, Category="Tongue")
	void LaunchTongue();

	UFUNCTION(BlueprintCallable, Category="Tongue")
	void ReleaseTongue();

	UFUNCTION(BlueprintPure, Category="Tongue")
	ETongueState GetTongueState() const { return TongueState; }

public:
	AFrogCharacter();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaTime) override;
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;
	virtual void NotifyControllerChanged() override;

	/** Zooms the diorama camera in (positive) or out (negative), in mouse-wheel notches. */
	UFUNCTION(BlueprintCallable, Category="Input")
	virtual void DoZoom(float Amount);

	FORCEINLINE USpringArmComponent* GetCameraBoom() const { return CameraBoom; }
	FORCEINLINE UCameraComponent* GetFollowCamera() const { return FollowCamera; }
	FORCEINLINE USkeletalMeshComponent* GetTongueMesh() const { return TongueMesh; }

protected:
	void ApplyCameraMode();
	void ApplyStylizedMesh();
	void TickLocomotion();
	FRotator GetMovementBasis() const;
	void EnsureZoomInput();

	UPROPERTY(Transient)
	TObjectPtr<UAnimSequence> CurrentLocomotionAnimation;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> ZoomMappingContext;

	void HandleTongueStarted();
	void HandleTongueCompleted();
	void HandleTongueCanceled();

	virtual void OnTongueAttached();
	virtual void UpdateTongueAttachment();
	virtual void OnTongueReleased();

	virtual void TickTongue(float DeltaTime);
	bool SetTongueState(ETongueState NewState);
	bool CanTransitionTongueState(ETongueState From, ETongueState To) const;
	bool TryGetTongueAnimInstance(UTongueAnimInstance*& OutAnimInstance);
	bool TryGetMouthLocation(FVector& OutLocation) const;
	void UpdateTonguePose(const FVector& RootLocation, const FVector& TipLocation, float ExtensionAlpha);
	void BeginTongueRetraction();
	void CompleteTongueRetraction();
	void ValidateTongueConfiguration();
	void DrawTongueDebug(const FVector& RootLocation, const FVector& TipLocation) const;

	float TongueStateTime = 0.0f;
	FVector TongueEndpoint = FVector::ZeroVector;
	FVector RetractionStartEndpoint = FVector::ZeroVector;
	FVector TongueTargetPointLocal = FVector::ZeroVector;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Tongue|State")
	TObjectPtr<AActor> TongueTargetActor;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="Tongue|State")
	TObjectPtr<UPrimitiveComponent> TongueTargetComponent;

	bool bWarnedMissingSocket = false;
	bool bWarnedMissingTongueMeshAsset = false;
	bool bWarnedMissingAnimInstance = false;
	bool bWarnedInvalidConfiguration = false;
	};
