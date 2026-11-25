package com.harvester.socialmediaharvester.architecture;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.relational.core.mapping.Table;
import org.springframework.data.repository.Repository;
import org.springframework.stereotype.Controller;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.RestController;

import com.harvester.socialmediaharvester.SocialMediaHarvesterApplication;
import com.harvester.socialmediaharvester.config.DatabaseCredentialsCheck;
import com.harvester.socialmediaharvester.service.FirstAdminService;
import com.tngtech.archunit.base.DescribedPredicate;
import com.tngtech.archunit.core.domain.JavaMethodCall;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/** The mechanical rules of CODING_STANDARDS.md. Main code only. */
@AnalyzeClasses(packagesOf = SocialMediaHarvesterApplication.class, importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureTest {

	private static final String ROOT = "com.harvester.socialmediaharvester";

	@ArchTest
	static final ArchRule configClassesLiveInConfig = classes()
			.that().areAnnotatedWith(Configuration.class)
			.or().haveSimpleNameEndingWith("Config")
			.or().haveSimpleNameEndingWith("Properties")
			.should().resideInAPackage(ROOT + ".config");

	@ArchTest
	static final ArchRule controllersLiveInController = classes()
			.that().areAnnotatedWith(RestController.class)
			.or().areAnnotatedWith(Controller.class)
			.or().haveSimpleNameEndingWith("Controller")
			.should().resideInAPackage(ROOT + ".controller");

	@ArchTest
	static final ArchRule servicesLiveInService = classes()
			.that().areAnnotatedWith(Service.class)
			.or().haveSimpleNameEndingWith("Service")
			.should().resideInAPackage(ROOT + ".service");

	@ArchTest
	static final ArchRule entitiesLiveInModel = classes()
			.that().areAnnotatedWith(Table.class)
			.should().resideInAPackage(ROOT + ".model");

	@ArchTest
	static final ArchRule repositoriesLiveInRepository = classes()
			.that().areAssignableTo(Repository.class)
			.or().haveSimpleNameEndingWith("Repository")
			.should().resideInAPackage(ROOT + ".repository");

	@ArchTest
	static final ArchRule controllersDoNotUseRepositories = noClasses()
			.that().resideInAPackage(ROOT + ".controller..")
			.should().dependOnClassesThat().resideInAPackage(ROOT + ".repository..");

	@ArchTest
	static final ArchRule noIPrefixedInterfaces = noClasses()
			.that().areInterfaces()
			.should().haveNameMatching(".*\\.I[A-Z][^.]*")
			.as("no interface is named I[A-Z]*");

	@ArchTest
	static final ArchRule onlyTheFirstAdminStartupWaits = noClasses()
			.that().doNotHaveFullyQualifiedName(FirstAdminService.class.getName())
			.should().callMethodWhere(new DescribedPredicate<JavaMethodCall>("Mono or Flux block*") {
				@Override
				public boolean test(JavaMethodCall call) {
					return (call.getTargetOwner().isAssignableTo(Mono.class)
							|| call.getTargetOwner().isAssignableTo(Flux.class))
							&& call.getName().startsWith("block");
				}
			})
			.because("ADR 0010: no .block() in application code, except the first-Admin startup check");

	@ArchTest
	static final ArchRule noJdbcOutsideFlywayAndTheCredentialsCheck = noClasses()
			.that().doNotHaveFullyQualifiedName(DatabaseCredentialsCheck.class.getName())
			.and().haveSimpleNameNotStartingWith("Flyway")
			.should().dependOnClassesThat().resideInAnyPackage("java.sql..", "javax.sql..", "org.springframework.jdbc..")
			.because("ADR 0010: Flyway migrations are the only JDBC use");
}
