import * as allure from 'allure-js-commons'

type FrontendLayer = 'base' | 'middle' | 'top'

export function applyFrontendAllureLabels(
  suiteName: string,
  layerName: FrontendLayer = 'base',
) {
  allure.parentSuite('Frontend')
  allure.suite(suiteName)
  allure.layer(layerName)
  allure.tag(`layer:${layerName}`)
}
